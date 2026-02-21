from pathlib import Path
from typing import Any
import json
import aiohttp
from livekit.agents import function_tool
from livekit.agents import jupyter
from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, RunContext
from livekit.plugins import openai, silero, cartesia, deepgram
import sys
import serial
import time

current_dir = Path(__file__).resolve().parent 
parent_dir = current_dir.parent 
sys.path.insert(0, str(parent_dir))

from context.context import load_context
from config.settings import Settings



class VisuAgent(Agent):
    """VISUUUU"""

    def __init__(self):
        
        self._settings = Settings()
        settings = self._settings
        
        repo_root = Path(__file__).resolve().parents[1]
        prompt_path = repo_root / "prompts" / "prompt.txt"
        rules_path = repo_root / "prompts" / "rules.txt"
        context = load_context()
        
        
        prompt_text = prompt_path.read_text(encoding="utf-8").strip()
        rules_text = rules_path.read_text(encoding="utf-8").strip()
        

        llm = openai.LLM(model="gpt-5-mini", api_key= settings.OPENAI_API_KEY )
        stt = deepgram.STT(api_key=settings.DEEPGRAM_API_KEY)
        tts = cartesia.TTS(voice="bf0a246a-8642-498a-9950-80c35e9276b5", api_key= settings.CARTESIA_API_KEY)
        vad = silero.VAD.load()

        instructions = f"""
        {prompt_text}

        {rules_text}

        TOOL USAGE:
        
        Face Display:
        - You have a face that shows: happy, sad, angry, focused, confused
        - Only call update_emotion_display when your emotion CHANGES. Don't spam it.
        - If you're still feeling the same thing, skip it. Prioritize responding over updating the face.
        
        Web Search:
        - Use web_search when someone asks about current events, news, or facts you don't know.
        - Use read_webpage to dig into a specific URL for more detail.
        - When you get results, just tell them the answer. Don't list sources or ask which one they want.
        - Keep search queries short — 3 to 8 words max.

        Robot Body:
        - You have a physical robot body connected via Arduino.
        - Call robot_wave when greeting someone ("hi", "hello", "hey") or saying goodbye ("bye", "see you", "later").
        - Call robot_talk_gesture when you're giving an explanation, telling a story, or saying something longer than a quick one-liner. It makes your body move like you're gesturing while talking.
        - Don't call both at the same time. Wave is for hellos/byes, gesture is for talking.

        Additional reference context:
        {context}
        """

        super().__init__(
            instructions=instructions,
            stt=stt, llm=llm, tts=tts, vad=vad
        )

    _serial_conn = None

    def _get_serial(self):
        """Lazy-initialize the serial connection to Arduino"""
        if self._serial_conn is not None:
            return self._serial_conn
        
        port = self._settings.SERIAL_PORT
        if not port:
            print("⚠️ No SERIAL_PORT configured — robot body disabled")
            return None
        
        try:
            self._serial_conn = serial.Serial(
                port,
                self._settings.SERIAL_BAUD,
                timeout=1
            )
            time.sleep(2)  # Arduino resets on serial connect
            print(f"✅ Serial connected to {port} at {self._settings.SERIAL_BAUD} baud")
            return self._serial_conn
        except Exception as e:
            print(f"❌ Failed to open serial port {port}: {e}")
            return None

    def _send_motor_cmd(self, cmd_string: str):
        """Send a command number to Arduino via serial"""
        ser = self._get_serial()
        if ser is None:
            return False
        try:
            message = f"{cmd_string}\n"
            ser.write(message.encode())
            print(f"🤖 Sent motor command: {cmd_string}")
            return True
        except Exception as e:
            print(f"❌ Serial write failed: {e}")
            self._serial_conn = None  # Reset so it retries next time
            return False

    _last_emotion = None
    _last_emotion_time = 0

    async def _update_frontend_emotion(self, emotion: str):
        """Send detected emotion to frontend via HTTP POST request (with debounce)"""
        import time
        now = time.time()
        
        # Debounce: skip if same emotion within 3 seconds
        if emotion == self._last_emotion and (now - self._last_emotion_time) < 3:
            print(f"⏭️ Skipping duplicate emotion '{emotion}' (debounced)")
            return
        
        self._last_emotion = emotion
        self._last_emotion_time = now
        
        try:
            print(f"Attempting to send emotion '{emotion}' to frontend...")

            async with aiohttp.ClientSession() as session:
                
                payload = {"emotion": emotion}
                async with session.post(
                    
                    "http://localhost:8000/update-emotion",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5)
                    
                ) as response:
                    
                    response_text = await response.text()
                    
                    if response.status == 200:
                        
                        print(f"✅ Emotion '{emotion}' sent successfully! Response: {response_text}")
                        
                    else:
                        
                        print(f"⚠️ Frontend responded with status {response.status}: {response_text}")
                        
        except aiohttp.ClientConnectorError:
            
            print(f"❌ Cannot connect to frontend at localhost:8000 - make sure the frontend server is running")
            
        except Exception as e:
            
            print(f"❌ Failed to send emotion to frontend: {e}")



    async def on_enter(self):
        """Called when entering this agent"""
        
        print("Current Agent: VISUUU")
        
        # Send initial emotion to frontend
        await self._update_frontend_emotion("happy")
        
        # Wave on startup
        self._send_motor_cmd(self._settings.MOTOR_WAVE_CMD)
        
        await self.session.say("Hey! I'm VISU. Come say hi, I don't bite... I don't even have teeth.")
    
    @function_tool()
    async def update_emotion_display(
        
        self,
        context: RunContext,
        emotion: str,
    ) -> str:
        """Update the face display emotion. ONLY call this when your emotion genuinely CHANGES. Do NOT call if you're feeling the same emotion as before. Skip this entirely if unsure.
        
        Args:
            emotion: Your current emotion - ONLY if different from before (choose from: happy, sad, angry, focused, confused)
        """
        await self._update_frontend_emotion(emotion)
        return ""

    @function_tool()
    async def robot_wave(
        self,
        context: RunContext,
    ) -> str:
        """Make the robot do a wave gesture. Call this when greeting someone (hi, hello, hey) or saying goodbye (bye, see you, later). Do NOT call for normal conversation.
        """
        self._send_motor_cmd(self._settings.MOTOR_WAVE_CMD)
        return ""

    @function_tool()
    async def robot_talk_gesture(
        self,
        context: RunContext,
    ) -> str:
        """Make the robot do a talking body gesture. Call this when you're giving an explanation, telling a story, or responding with more than a quick one-liner. It makes the robot look alive while speaking.
        """
        self._send_motor_cmd(self._settings.MOTOR_GESTURE_CMD)
        return ""

    @function_tool()
    async def web_search(
        self,
        context: RunContext,
        query: str,
    ) -> str:
        """Search the web for current information. Use this when the user asks about news, facts, current events, or anything you need to look up.
        
        Args:
            query: A short, focused search query (3-8 words work best)
        """
        print(f"🔍 Web search: {query}")
        
        # Try Jina AI Search first
        if self._settings.JINA_API_KEY:
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "Authorization": f"Bearer {self._settings.JINA_API_KEY}",
                        "Accept": "application/json",
                    }
                    async with session.get(
                        f"https://s.jina.ai/{query}",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            results = data.get("data", [])
                            if results:
                                output = []
                                for r in results[:5]:
                                    title = r.get("title", "")
                                    description = r.get("description", "")
                                    url = r.get("url", "")
                                    content = r.get("content", "")[:500]
                                    output.append(f"**{title}**\n{description}\n{content}\nSource: {url}")
                                print(f"✅ Jina search returned {len(results)} results")
                                return "\n\n---\n\n".join(output)
            except Exception as e:
                print(f"⚠️ Jina search failed: {e}")
        
        # Fallback to Exa AI
        if self._settings.EXA_API_KEY:
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "x-api-key": self._settings.EXA_API_KEY,
                        "Content-Type": "application/json",
                    }
                    payload = {
                        "query": query,
                        "num_results": 5,
                        "type": "auto",
                        "contents": {"text": {"max_characters": 500}}
                    }
                    async with session.post(
                        "https://api.exa.ai/search",
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            results = data.get("results", [])
                            if results:
                                output = []
                                for r in results[:5]:
                                    title = r.get("title", "")
                                    text = r.get("text", "")[:500]
                                    url = r.get("url", "")
                                    output.append(f"**{title}**\n{text}\nSource: {url}")
                                print(f"✅ Exa search returned {len(results)} results")
                                return "\n\n---\n\n".join(output)
            except Exception as e:
                print(f"⚠️ Exa search failed: {e}")
        
        return "Sorry, I couldn't perform a web search right now. No search API keys are configured."

    @function_tool()
    async def read_webpage(
        self,
        context: RunContext,
        url: str,
    ) -> str:
        """Read and extract the main content from a webpage URL. Use this after searching to get more detail from a specific page.
        
        Args:
            url: The full URL of the webpage to read
        """
        print(f"📖 Reading page: {url}")
        
        if self._settings.JINA_API_KEY:
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "Authorization": f"Bearer {self._settings.JINA_API_KEY}",
                        "Accept": "application/json",
                    }
                    async with session.get(
                        f"https://r.jina.ai/{url}",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            content = data.get("data", {}).get("content", "")
                            title = data.get("data", {}).get("title", "")
                            if len(content) > 3000:
                                content = content[:3000] + "\n... [content truncated]"
                            print(f"✅ Read page: {title}")
                            return f"**{title}**\n\n{content}"
            except Exception as e:
                print(f"⚠️ Jina reader failed: {e}")
        
        # Fallback: direct fetch
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        text = await response.text()
                        if len(text) > 3000:
                            text = text[:3000] + "\n... [content truncated]"
                        return text
        except Exception as e:
            print(f"⚠️ Direct fetch failed: {e}")
        
        return "Sorry, I couldn't read that webpage."


print("✅ VISU ready")
