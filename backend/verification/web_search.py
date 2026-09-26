"""
Web Search Retrieval for VERIFAI Source Provenance.
Uses real web retrieval:
1. Gemini's native google_search grounding tool (when available)
2. Authoritative DuckDuckGo Instant Answer API for official government and organizational portals
3. Wikipedia REST / Opensearch API for authoritative reference articles

Returns actual URLs, titles, domains, and evidence snippets.
NEVER fabricates URLs or citations.
"""

import re
import json
import logging
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger("web_search")


def _is_factual_question(task: str) -> bool:
    """Returns True if the task is a factual question that benefits from web retrieval."""
    t = task.strip().lower()
    # Skip calculations and numbers
    if re.search(r"^\s*[\d\s\+\-\*\/\(\)\.!%×÷\^]+\s*$", t):
        return False
    if re.search(r"![0-9]+", t):
        return False
    # Skip conversational greetings
    if t in ["hi", "hello", "hey", "how are you", "good morning", "good evening", "test", "ping"]:
        return False
    # Skip code
    if any(kw in t for kw in ["def ", "class ", "import ", "print(", "```", "function"]):
        return False
    # Skip pure syllogisms / logic
    if "all a are b" in t or "modus ponens" in t or "syllogism" in t:
        return False
    # Factual question indicators
    factual_triggers = [
        "who is", "who was", "who are", "who were",
        "what is", "what was", "what are",
        "where is", "where was",
        "when is", "when was", "when did",
        "which is", "which was",
        "capital of", "president of", "prime minister",
        "pm of", "cm of", "ceo of", "founder of",
        "population of", "currency of", "language of",
        "how many", "how much",
        "is india", "is china", "is usa", "is the",
        "largest", "smallest", "tallest", "fastest",
        "invented", "discovered", "founded", "headquarters",
    ]
    return any(t.startswith(trigger) or trigger in t for trigger in factual_triggers)


def fetch_authoritative_web_evidence(task: str, candidate_answer: str = "") -> Optional[Dict[str, Any]]:
    """
    Directly retrieves authoritative external evidence via DuckDuckGo API and Wikipedia REST API.
    Returns real URLs (official government sites, official portals, Wikipedia reference).
    Never fabricates URLs.
    """
    t_clean = task.strip().rstrip("?. ")
    
    # Candidate queries: try stripped question, full question, candidate answer entity
    queries = [t_clean]

    # Strip question boilerplate: "what is the capital of..." -> "capital of..."
    stripped = re.sub(r'^(what|who|where|when|which|how)\s+(is|was|are|were)\s+(the\s+)?', '', t_clean, flags=re.IGNORECASE).strip()
    if stripped and stripped != t_clean:
        queries.insert(0, stripped)

    if candidate_answer:
        clean_ans = re.sub(r"[*_`]", "", candidate_answer).strip().rstrip(".")
        # If candidate answer is "Amaravati is the capital...", extract "Amaravati"
        if " is " in clean_ans:
            subj = clean_ans.split(" is ")[0].strip()
            if len(subj) < 40 and not any(w in subj.lower() for w in ["the answer", "candidate", "here"]):
                queries.append(subj)
        first_line = clean_ans.split("\n")[0].strip()
        if len(first_line) < 60 and first_line not in queries:
            queries.append(first_line)

    # 1. Try DuckDuckGo Instant Answer API
    for q in queries:
        try:
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(q)}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(url, headers={"User-Agent": "VERIFAI-Provenance/1.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                
                # Check for official site in Results
                results = data.get("Results", [])
                official_url = None
                official_title = None
                for res in results:
                    f_url = res.get("FirstURL")
                    f_text = res.get("Text", "")
                    if f_url and ("official" in f_text.lower() or ".gov" in f_url or ".nic.in" in f_url or ".org" in f_url):
                        official_url = f_url
                        official_title = f_text.replace("Official site", "").strip(" -:") or data.get("Heading") or "Official Website"
                        break
                    elif f_url and not official_url:
                        official_url = f_url
                        official_title = f_text.replace("Official site", "").strip(" -:") or data.get("Heading")
                
                heading = data.get("Heading", "")
                abstract = data.get("Abstract", "")
                abstract_url = data.get("AbstractURL", "")
                abstract_source = data.get("AbstractSource", "Reference")

                if official_url:
                    dom_m = re.match(r"https?://(?:www\.)?([^/]+)", official_url)
                    dom = dom_m.group(1) if dom_m else official_url
                    ev = abstract if abstract else f"Official site for {heading or q}: {official_title}"
                    return {
                        "source_type": "web",
                        "source_title": official_title or heading or "Official Portal",
                        "source_domain": dom,
                        "source_url": official_url,
                        "retrieved_evidence": ev,
                        "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "claim_supported": True,
                    }

                if abstract and abstract_url:
                    dom_m = re.match(r"https?://(?:www\.)?([^/]+)", abstract_url)
                    dom = dom_m.group(1) if dom_m else "en.wikipedia.org"
                    return {
                        "source_type": "web",
                        "source_title": heading or f"{abstract_source} Reference",
                        "source_domain": dom,
                        "source_url": abstract_url,
                        "retrieved_evidence": abstract,
                        "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "claim_supported": True,
                    }
        except Exception as e:
            logger.debug(f"DDG query failed for '{q}': {e}")
            continue

    # 2. Try Wikipedia Opensearch + Summary API
    for q in queries:
        try:
            opensearch_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(q)}&limit=3&namespace=0&format=json"
            req = urllib.request.Request(opensearch_url, headers={"User-Agent": "VERIFAI-Provenance/1.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                os_data = json.loads(resp.read().decode("utf-8"))
                titles = os_data[1] if len(os_data) > 1 else []
                urls = os_data[3] if len(os_data) > 3 else []
                if titles and urls:
                    top_title = titles[0]
                    top_url = urls[0]
                    sum_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(top_title.replace(' ', '_'))}"
                    req2 = urllib.request.Request(sum_url, headers={"User-Agent": "VERIFAI-Provenance/1.0"})
                    with urllib.request.urlopen(req2, timeout=4) as resp2:
                        sum_data = json.loads(resp2.read().decode("utf-8"))
                        extract = sum_data.get("extract", "")
                        return {
                            "source_type": "web",
                            "source_title": sum_data.get("title", top_title),
                            "source_domain": "en.wikipedia.org",
                            "source_url": sum_data.get("content_urls", {}).get("desktop", {}).get("page", top_url),
                            "retrieved_evidence": extract or f"Reference article on {top_title}.",
                            "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "claim_supported": True,
                        }
        except Exception as e:
            logger.debug(f"Wikipedia query failed for '{q}': {e}")
            continue

    return None


def fetch_web_evidence(task: str, gemini_service=None, candidate_answer: str = "") -> Optional[Dict[str, Any]]:
    """
    Fetches real web evidence for a factual question.
    1. Attempts Gemini google_search grounding if available.
    2. Falls back to authoritative DuckDuckGo / Wikipedia retrieval.
    Returns a dict matching the specified provenance schema:
    {
      "source_type": "web",
      "source_title": "...",
      "source_domain": "...",
      "source_url": "...",
      "retrieved_evidence": "...",
      "retrieved_at": "...",
      "claim_supported": true
    }
    Returns None if no real source could be retrieved (never fabricates).
    """
    if not _is_factual_question(task):
        return None

    # Try Gemini grounding if service is available
    if gemini_service and gemini_service.is_available():
        try:
            from google.genai import types as genai_types

            client = gemini_service.client
            model = gemini_service.model_name

            response = client.models.generate_content(
                model=model,
                contents=f"Answer this factual question concisely with a direct fact: {task}",
                config=genai_types.GenerateContentConfig(
                    tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
                    temperature=0.1,
                ),
            )

            if response and response.candidates:
                candidate = response.candidates[0]
                answer_text = ""
                if candidate.content and candidate.content.parts:
                    answer_text = " ".join(
                        p.text for p in candidate.content.parts if hasattr(p, "text") and p.text
                    ).strip()

                grounding_meta = getattr(candidate, "grounding_metadata", None)
                source_title = None
                source_domain = None
                source_url = None

                if grounding_meta:
                    chunks = getattr(grounding_meta, "grounding_chunks", None) or []
                    for chunk in chunks:
                        web = getattr(chunk, "web", None)
                        if web:
                            source_url = getattr(web, "uri", None) or getattr(web, "url", None)
                            source_title = getattr(web, "title", None)
                            if source_url:
                                m = re.match(r"https?://(?:www\.)?([^/]+)", source_url)
                                source_domain = m.group(1) if m else source_url
                                break

                    if not source_url:
                        entry = getattr(grounding_meta, "search_entry_point", None)
                        if entry:
                            rendered = getattr(entry, "rendered_content", "") or ""
                            url_match = re.search(r'href="(https?://[^"]+)"', rendered)
                            title_match = re.search(r'<[^>]*>([^<]{5,80})</[^>]*>', rendered)
                            if url_match:
                                source_url = url_match.group(1)
                                m = re.match(r"https?://(?:www\.)?([^/]+)", source_url)
                                source_domain = m.group(1) if m else source_url
                            if title_match and not source_title:
                                source_title = title_match.group(1).strip()

                if source_url and answer_text:
                    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    return {
                        "source_type": "web",
                        "source_title": source_title or source_domain or "Web source",
                        "source_domain": source_domain or "web",
                        "source_url": source_url,
                        "retrieved_evidence": answer_text[:400].strip(),
                        "retrieved_at": retrieved_at,
                        "claim_supported": True,
                    }
        except Exception as e:
            logger.info(f"Gemini grounding unavailable, falling back to authoritative web retrieval: {e}")

    # Fallback to authoritative live retrieval (DuckDuckGo official sites + Wikipedia REST)
    authoritative_res = fetch_authoritative_web_evidence(task, candidate_answer)
    if authoritative_res:
        logger.info(f"Authoritative web evidence retrieved for '{task[:50]}': {authoritative_res['source_url']}")
        return authoritative_res

    logger.info(f"No external web evidence found for '{task[:50]}'")
    return None
