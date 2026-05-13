import os
import json
import re
import base64
from io import BytesIO
from groq import Groq

from .config import GROQ_API_KEY, SYSTEM_PROMPT, GROQ_TEXT_MODEL, GROQ_VISION_MODEL
from .memory import save_conversation, get_recent_history

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def check_and_extract_facts():
    from .memory import should_extract_facts, get_recent_history, save_core_fact
    if should_extract_facts() and groq_client:
        try:
            history = get_recent_history(limit=10)
            prompt = 'Analyze the following conversation and extract new, permanent facts about the user (e.g., name, studies, preferences). Return ONLY a JSON object: {"facts": [{"key": "name", "value": "John"}]}. Return empty list if no facts.'
            
            messages = [{"role": "system", "content": prompt}]
            messages.extend(history)
            
            response = groq_client.chat.completions.create(
                model=GROQ_TEXT_MODEL,
                messages=messages,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            for fact in data.get("facts", []):
                save_core_fact(fact["key"], fact["value"])
        except Exception as e:
            print("Fact extraction error:", e)

def get_jinu_response(message: str, image=None) -> str:
    try:
        # Get Semantic Memories and Core Facts
        from .memory import get_relevant_memories, get_core_facts
        
        core_facts = get_core_facts(limit=10)
        dynamic_prompt = SYSTEM_PROMPT
        if core_facts:
            facts_str = "\n".join([f"- {row[0]}: {row[1]}" for row in core_facts])
            dynamic_prompt += f"\n\nCore User Facts:\n{facts_str}"
            
        memories = get_relevant_memories(message)
        contextual_message = message
        if memories:
            contextual_message = f"Relevant past memories:\n{memories}\n\nUser Message:\n{message}"
            
        history = get_recent_history()
        
        if not groq_client:
            return "Error: Please set your GROQ_API_KEY in the .env file!"
            
        messages = [{"role": "system", "content": dynamic_prompt}]
        messages.extend(history)
        
        if image:
            buffered = BytesIO()
            image.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            content = [
                {"type": "text", "text": contextual_message},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}}
            ]
            messages.append({"role": "user", "content": content})
            
            response = groq_client.chat.completions.create(
                model=GROQ_VISION_MODEL,
                messages=messages
            )
        else:
            messages.append({"role": "user", "content": contextual_message})
            response = groq_client.chat.completions.create(
                model=GROQ_TEXT_MODEL,
                messages=messages
            )
            
        reply_text = response.choices[0].message.content
        
        # Check if reply is a JSON action
        from .task import execute_task
        json_match = re.search(r'\{.*\}', reply_text, re.DOTALL)
        if json_match:
            try:
                task_json = json.loads(json_match.group(0))
                if "action" in task_json:
                    task_result = execute_task(task_json)
                    reply_text = f"Action executed: {task_result}"
            except json.JSONDecodeError:
                pass
        
        # Save to DB
        save_conversation(message, reply_text)
        
        # Async fact extraction if needed
        import threading
        threading.Thread(target=check_and_extract_facts).start()
        
        return reply_text
    except Exception as e:
        print(f"Error in brain.py: {e}")
        return f"Sorry, my brain encountered an error: {str(e)}"

def generate_proactive_message(trigger_type: str, context: str) -> str:
    if not groq_client:
        return "I noticed something, but my API key is missing!"
        
    try:
        prompt = f"The system has triggered an event of type '{trigger_type}' with context: '{context}'. Please generate a short, proactive, conversational message to the user addressing this. Keep it to one sentence if possible."
        
        response = groq_client.chat.completions.create(
            model=GROQ_TEXT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )
        reply_text = response.choices[0].message.content
        
        # Save to DB (Proactive messages are JINU replies with system as user message)
        save_conversation(f"[SYSTEM TRIGGER: {trigger_type}] {context}", reply_text, tags="proactive")
        
        return reply_text
    except Exception as e:
        print(f"Error generating proactive message: {e}")
        return "Hey! I noticed something but had an error talking to my brain."
