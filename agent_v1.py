import json
import os
import requests
from dataclasses import dataclass
from typing import List, Any
import argparse
import subprocess
import re
import time

# --- Configuration ---
OLLAMA_API_BASE = "http://localhost:11434/api/generate"
# Default local models (adjust names to what you pulled in Ollama)
SIMPLE_MODEL = "qwen3:0.6b"  # for short/reflection tasks (local)
COMPLEX_MODEL = "gemma3:latest"  # for decomposition and planning (local)
MEMORY_FILE = "agent_memory.txt"
# If True, call Ollama via CLI first (faster/avoids HTTP timeouts); set False to prefer HTTP API
PREFER_CLI = True


class OllamaClient:
    """Minimal Ollama client. If Ollama isn't available, falls back to simple simulated responses."""
    def invoke(self, model_name: str, prompt: str, expect_json: bool = False) -> str:
        """Invoke a local Ollama model via CLI (preferred) or HTTP API, with fallback to simulation.

        If expect_json=True the CLI will request JSON format and the HTTP response is handled accordingly.
        """
        print(f"\n[LLM invoke] model={model_name} prompt_snippet={prompt[:160].replace('\n',' ')}...")
        payload = {"model": model_name, "prompt": prompt, "stream": False}

        # 1) Try CLI first (avoids some HTTP timeout issues)
        if PREFER_CLI:
            try:
                cmd = ["ollama", "run", model_name, prompt, "--hidethinking"]
                if expect_json:
                    cmd += ["--format", "json"]
                proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
                if proc.returncode == 0 and proc.stdout:
                    out = proc.stdout.strip()
                    # If caller requested structured JSON, return raw stdout for parsing
                    if expect_json:
                        return out
                    return self._clean_output(out)
                else:
                    print(f"[WARN] 'ollama run' exited {proc.returncode}. Stderr: {proc.stderr}")
            except Exception as e:
                print(f"[WARN] Ollama CLI attempt failed: {e}")

        # 2) Try HTTP API (with a couple retries)
        attempts = 2
        for attempt in range(1, attempts + 1):
            try:
                resp = requests.post(OLLAMA_API_BASE, json=payload, headers={"Content-Type": "application/json"}, timeout=120)
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, dict) and "response" in data:
                    if expect_json and isinstance(data.get("response", ""), (dict, list)):
                        return json.dumps(data.get("response", ""))
                    return self._clean_output(data.get("response", ""))
                return self._clean_output(json.dumps(data))
            except Exception as e:
                if attempt < attempts:
                    print(f"[WARN] Ollama HTTP attempt {attempt} failed: {e}. Retrying...")
                    continue
                print(f"[WARN] Ollama HTTP attempts failed: {e}")

        # 3) Final fallback: simulated response
        print(f"[WARNING] Using fallback/simulated response.")
        return self._simulate_response(model_name, prompt)

    def _simulate_response(self, model_name: str, prompt: str) -> str:
        # Very small heuristics to produce JSON lists for mission/command prompts
        lower = prompt.lower()
        if "break this down into" in lower or "break this mission" in lower or "ultimate mission" in lower:
            # produce 3 simple commands by splitting mission nouns
            base = "Automatically generate commands based on the mission"
            return json.dumps(["Research requirements", "Draft content", "Review & finalize"]) 
        if "create a detailed" in lower or "create a plan" in lower:
            return json.dumps(["Step 1: Analyze", "Step 2: Implement", "Step 3: Test & polish"]) 
        if "what is one concise lesson" in lower or "what is one concise lesson i can learn" in lower:
            return "Keep tasks small and verify output formats before trusting the model." 
        # Generic fallback: return the prompt echoed
        return json.dumps([s.strip() for s in (prompt.split("\n")[:3]) if s.strip()])

    def _clean_output(self, text: str) -> str:
        """Remove common artifacts from model output: markdown fences, <think> tokens, excessive whitespace."""
        if not isinstance(text, str):
            return ""
        # Remove markdown fences and code blocks
        text = re.sub(r"```[\s\S]*?```", "", text)
        # Remove simple inline code fences
        text = text.replace('`', '')
        # Remove <think> or similar assistant markers and common 'thinking' phrases
        text = re.sub(r"<\/?think>|\[think\]|\(think\)|\bthinking\.\.\.|\.\.\.done thinking\.|\bdone thinking\.|\b\(thinking\)\b", "", text, flags=re.IGNORECASE)
        # Remove common assistant chain-of-thought starters
        text = re.sub(r"\b(okay,? let(?:'s)? see|let me think(?: about that)?|i need to think|thinking)[:\.,]?\s*", "", text, flags=re.IGNORECASE)
        # Remove 'SUCCESS:' or 'Result:' prefixes that are part of simulated results
        text = re.sub(r"\bSUCCESS:\s*", "", text)
        text = re.sub(r"\bResult:\s*", "", text)
        # Collapse repeated whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text


from memory_store import MemoryStore

# Backwards-compatible alias for the older SimpleMemory name used elsewhere
class SimpleMemory(MemoryStore):
    pass


@dataclass
class Task:
    task_type: str  # mission, command, plan_step
    content: Any


class ModelRouter:
    """Choose a model name based on a simple complexity heuristic."""

    @staticmethod
    def estimate_complexity(text: str) -> str:
        # Very naive heuristic: presence of certain keywords or length
        keywords = ["person", "character", "complex", "research", "analysis", "design", "architecture"]
        if any(k in text.lower() for k in keywords) or len(text.split()) > 60:
            return "complex"
        return "simple"

    @staticmethod
    def select_model_for(task_kind: str, text: str) -> str:
        # task_kind: 'decompose'|'plan'|'reflect' etc.
        comp = ModelRouter.estimate_complexity(text)
        if task_kind == "reflect":
            return SIMPLE_MODEL
        if comp == "complex":
            return COMPLEX_MODEL
        return SIMPLE_MODEL


class SimplifiedAgent:
    def __init__(self, mission: str):
        self.client = OllamaClient()
        self.memory = SimpleMemory()
        self.task_queue: List[Task] = [Task(task_type="mission", content=mission)]

    def _decompose_mission_to_commands(self, mission: str):
        print("\n>>> Decomposing mission to commands...")
        prompt = f"""
        Given the ultimate mission: "{mission}"

        Break this down into a series of 3-5 high-level, actionable commands.
        IMPORTANT: Do NOT include chain-of-thought, internal reasoning, or any commentary.
        Respond ONLY with a valid JSON array of strings and nothing else. Example: ["command 1", "command 2"]
        """
        model = ModelRouter.select_model_for("decompose", mission)
        # Enforce structured JSON array response with limited retries (3 attempts, 0.5s delay)
        response = None
        for attempt in range(1, 4):
            strict = prompt + "\nIMPORTANT: Respond ONLY with a valid JSON array of strings like [\"cmd1\", \"cmd2\"] and nothing else."
            resp = self.client.invoke(model, strict, expect_json=True)
            arr_text = self._extract_json_array(resp)
            if arr_text:
                # validate array contains extractable strings (reject arrays with dicts that have no string fields)
                try:
                    parsed = json.loads(arr_text)
                    valid_items = []
                    ok = True
                    for el in parsed:
                        if isinstance(el, str) and el.strip():
                            valid_items.append(el.strip())
                        elif isinstance(el, dict):
                            candidate = None
                            for k in ("response", "lesson", "text", "result", "message"):
                                if k in el and isinstance(el[k], str) and el[k].strip():
                                    candidate = el[k].strip()
                                    break
                            if candidate:
                                valid_items.append(candidate)
                            else:
                                ok = False
                                break
                        else:
                            txt = str(el).strip()
                            if txt:
                                valid_items.append(txt)
                            else:
                                ok = False
                                break
                    if ok and valid_items:
                        response = json.dumps(valid_items)
                        break
                except Exception:
                    pass
            # small backoff between retries
            if attempt < 3:
                time.sleep(0.5)
        if not response:
            # last attempt: accept whatever and fallback parsing
            resp = self.client.invoke(model, prompt, expect_json=True)
            response = resp
        commands = self._parse_json_list_or_fallback(response, fallback_count=3)
        for cmd in reversed(commands):
            self.task_queue.insert(0, Task(task_type="command", content=cmd))

    def _decompose_command_to_plan(self, command: str):
        print(f"\n>>> Decomposing command to plan: {command}")
        memory_context = self.memory.get_context()
        prompt = f"""
        {memory_context}

        Given the command: "{command}"

        Create a detailed, step-by-step plan to execute this command. Each step should be a single, clear action.
        IMPORTANT: Do NOT include chain-of-thought or explanations. Respond ONLY with a valid JSON array of strings and nothing else. Example: ["step 1", "step 2"]
        """
        model = ModelRouter.select_model_for("plan", command)
        # enforce structured JSON array with retries (3 attempts, 0.5s delay)
        response = None
        for attempt in range(1, 4):
            strict = prompt + "\nIMPORTANT: Respond ONLY with a valid JSON array of strings like [\"step1\", \"step2\"] and nothing else."
            resp = self.client.invoke(model, strict, expect_json=True)
            arr_text = self._extract_json_array(resp)
            if arr_text:
                try:
                    parsed = json.loads(arr_text)
                    valid_items = []
                    ok = True
                    for el in parsed:
                        if isinstance(el, str) and el.strip():
                            valid_items.append(el.strip())
                        elif isinstance(el, dict):
                            candidate = None
                            for k in ("response", "lesson", "text", "result", "message"):
                                if k in el and isinstance(el[k], str) and el[k].strip():
                                    candidate = el[k].strip()
                                    break
                            if candidate:
                                valid_items.append(candidate)
                            else:
                                ok = False
                                break
                        else:
                            txt = str(el).strip()
                            if txt:
                                valid_items.append(txt)
                            else:
                                ok = False
                                break
                    if ok and valid_items:
                        response = json.dumps(valid_items)
                        break
                except Exception:
                    pass
            if attempt < 3:
                time.sleep(0.5)
        if not response:
            resp = self.client.invoke(model, prompt, expect_json=True)
            response = resp
        steps = self._parse_json_list_or_fallback(response, fallback_count=3)
        for s in reversed(steps):
            self.task_queue.insert(0, Task(task_type="plan_step", content=s))

    def _execute_plan_step(self, step: str):
        print(f"\n>>> Executing step: {step}")
        # V1 simulation: return a success string
        return f"SUCCESS: {step}"

    def _reflect_and_optimize(self, completed_step: str, result: str):
        print(f"\n>>> Reflecting on step: {completed_step}")
        prompt = f"""
I am an autonomous agent. I just performed an action.
Action: "{completed_step}"
Result: "{result}"

    Based on this, produce ONE concise lesson or takeaway I can learn to improve my future performance.
    Respond with a single short sentence only. Do NOT include any explanation or reasoning.
    The lesson should be a short, memorable sentence.
"""
        model = ModelRouter.select_model_for("reflect", completed_step)
        # Stronger: ask the model to return only a JSON object like {"lesson":"..."} and retry
        lesson_full = ""
        max_retries = 2
        for attempt in range(1, max_retries + 1):
            # stricter instruction: return a JSON object with key "lesson"
            strict_prompt = prompt + "\nIMPORTANT: Respond ONLY with a JSON object exactly like {\"lesson\": \"...\"} and nothing else."
            lesson_resp = self.client.invoke(model, strict_prompt, expect_json=True)
            # Try to parse the response as JSON first
            parsed = None
            try:
                parsed = json.loads(lesson_resp)
            except Exception:
                # sometimes CLI returns cleaned text; try to clean and parse again
                try:
                    cleaned = self.client._clean_output(lesson_resp or "")
                    parsed = json.loads(cleaned)
                except Exception:
                    parsed = None

            if isinstance(parsed, dict):
                # prefer explicit 'lesson' key
                if isinstance(parsed.get("lesson"), str) and parsed.get("lesson").strip():
                    lesson_full = parsed.get("lesson").strip()
                    break
                # otherwise try common string fields
                for k in ("response", "result", "message", "text"):
                    if isinstance(parsed.get(k), str) and parsed.get(k).strip():
                        lesson_full = parsed.get(k).strip()
                        break
                if lesson_full:
                    break
            elif isinstance(parsed, str):
                lesson_full = parsed.strip()
                break
            # If parsing failed or returned other structure, allow a final fallback try without strict JSON
            if attempt == max_retries:
                # fallback parsing heuristics (previous behavior)
                try:
                    parsed2 = json.loads(lesson_resp)
                    if isinstance(parsed2, list) and parsed2:
                        for el in parsed2:
                            if isinstance(el, str) and el.strip():
                                lesson_full = el.strip()
                                break
                    elif isinstance(parsed2, dict):
                        for k in ("lesson", "response", "result", "message", "text"):
                            if k in parsed2 and isinstance(parsed2[k], str) and parsed2[k].strip():
                                lesson_full = parsed2[k].strip()
                                break
                except Exception:
                    lesson_full = self.client._clean_output(lesson_resp or "")

        # Post-process: keep only first sentence, remove thought markers, limit length
        # split into sentences by punctuation
        sentences = re.split(r'[\.\!?]\s+', lesson_full)
        lesson_candidate = sentences[0].strip() if sentences and sentences[0].strip() else (lesson_full.splitlines()[0].strip() if lesson_full else "")
        # aggressive sanitization: remove chain-of-thought fragments
        lesson_candidate = re.sub(r"<\/?think>|\[think\]|\(think\)|\b(okay|let(?:'s)? see|i need to think|thinking)\b[:\.,]?", "", lesson_candidate, flags=re.IGNORECASE)
        lesson_candidate = re.sub(r"\s+", " ", lesson_candidate).strip()
        # truncate to reasonable length
        if len(lesson_candidate) > 160:
            lesson_candidate = lesson_candidate[:157].rsplit(' ', 1)[0] + '...'
        # final validity check
        if not lesson_candidate or len(lesson_candidate) < 8:
            lesson_candidate = "Keep tasks small and verify outputs."
        self.memory.add_lesson(lesson_candidate)

    def _parse_json_list_or_fallback(self, response: str, fallback_count: int = 3) -> List[str]:
        # Try to parse as JSON list of strings
        # First try to extract a JSON array substring if it's embedded in text
        try:
            arr_text = self._extract_json_array(response)
            if arr_text:
                parsed = json.loads(arr_text)
                if isinstance(parsed, list):
                    items: List[str] = []
                    for x in parsed:
                        if isinstance(x, str) and x.strip():
                            items.append(x.strip())
                        elif isinstance(x, dict):
                            # prefer specific keys
                            candidate = None
                            for k in ("response", "lesson", "text", "result", "message"):
                                if k in x and isinstance(x[k], str) and x[k].strip():
                                    candidate = x[k].strip()
                                    break
                            if not candidate:
                                # take first string value
                                for v in x.values():
                                    if isinstance(v, str) and v.strip():
                                        candidate = v.strip()
                                        break
                            if candidate:
                                items.append(candidate)
                            else:
                                # fallback to compact JSON string
                                items.append(json.dumps(x))
                        else:
                            txt = str(x).strip()
                            if txt:
                                items.append(txt)
                    return items[:fallback_count]
        except Exception:
            pass
        # Fallback heuristics: split by newlines and punctuation
        lines = [l.strip() for l in response.splitlines() if l.strip()]
        if not lines:
            # fallback to generic placeholders
            return [f"Fallback step {i+1}" for i in range(fallback_count)]
        # If lines contain numbered items, extract them
        items = []
        for l in lines:
            # remove numbering like '1.' or '- '
            cleaned = l
            if cleaned.lstrip().startswith(('-', '*')):
                cleaned = cleaned.lstrip('-* ').strip()
            # remove leading digits
            cleaned = cleaned.lstrip('0123456789. ').strip()
            if cleaned:
                items.append(cleaned)
        if items:
            return items[:fallback_count]
        # last resort: split by commas
        parts = [p.strip() for p in (response.split(',')) if p.strip()]
        if parts:
            return parts[:fallback_count]
        return [f"Fallback step {i+1}" for i in range(fallback_count)]

    def _extract_json_array(self, text: str) -> str | None:
        """Find the first top-level JSON array in the text and return it as a string, or None."""
        if not isinstance(text, str):
            return None
        # find first '[' and then find the matching closing ']' accounting for nested brackets
        start = text.find('[')
        if start == -1:
            return None
        depth = 0
        for i in range(start, len(text)):
            c = text[i]
            if c == '[':
                depth += 1
            elif c == ']':
                depth -= 1
                if depth == 0:
                    candidate = text[start:i+1]
                    # quick sanity check
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, list):
                            return candidate
                    except Exception:
                        return None
        return None

    def run(self):
        while self.task_queue:
            current = self.task_queue.pop(0)
            if current.task_type == "mission":
                self._decompose_mission_to_commands(current.content)
            elif current.task_type == "command":
                self._decompose_command_to_plan(current.content)
            elif current.task_type == "plan_step":
                result = self._execute_plan_step(current.content)
                self._reflect_and_optimize(current.content, result)
        print("\n===== Mission Accomplished =====")
        # One-time sanitize memory file now that the run has finished to remove legacy noisy entries
        try:
            # Run enhanced sanitization to aggressively remove noisy artifacts
            self.memory.sanitize_existing()
            print("[Memory] Sanitized and reloaded memory file.")
            # Trigger embedding generation for new/updated lessons (best-effort)
            try:
                print('[Memory] Generating/refreshing embeddings...')
                # embed_lessons will attempt sentence-transformers or transformers fallback
                self.memory.embed_lessons()
                print('[Memory] Embeddings refreshed.')
            except Exception as _e:
                print(f'[Memory] Embedding refresh failed: {_e}')
        except Exception:
            pass
        print(self.memory.get_context())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simplified MCP agent V1')
    parser.add_argument('--mission', '-m', type=str, default=("Draft a short but exciting feature announcement for the new 'Market Insights & Paid Reports' "
                                                                 "system on the 'beginnings' freelancing platform."), help='Mission prompt')
    args = parser.parse_args()
    agent = SimplifiedAgent(mission=args.mission)
    agent.run()
