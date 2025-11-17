import os
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough

# Load environment variables
load_dotenv()

try:
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
except ImportError:
    try:
        from langchain_community.chat_models import ChatGoogleGenerativeAI
        from langchain_community.embeddings import GoogleGenerativeAIEmbeddings
    except ImportError:
        raise ImportError("Please install langchain-google-genai: pip install langchain-google-genai")

try:
    from langchain_chroma import Chroma
except ImportError:
    # Fallback to langchain_community for older versions
    from langchain_community.vectorstores import Chroma

from skills.code_runner import CodeRunnerSkill
from skills.time_tool import TimeTool
from skills.web_search import WebSearchSkill


class MaddyBotAgent:
    """Core controller for MaddyBot 2.0 interactions."""

    def __init__(self, model_name: str = "gemini-2.5-flash", memory_path: str = "./memory", api_key: Optional[str] = None) -> None:
        self.model_name = model_name
        self.memory_path = memory_path
        self.max_history_messages = 6  # Reduced for faster responses
        
        # Get API key from parameter, environment variable, or .env file
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "Google API key is required. Set it as:\n"
                "1. Environment variable: GOOGLE_API_KEY or GEMINI_API_KEY\n"
                "2. Create a .env file with: GOOGLE_API_KEY=your_key_here\n"
                "3. Pass it to MaddyBotAgent(api_key='your_key_here')\n"
                "Get your API key from: https://makersuite.google.com/app/apikey"
            )

        os.makedirs(self.memory_path, exist_ok=True)

        # Configure Gemini LLM - optimized for speed
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=self.api_key,
            temperature=0.7,  # Balanced creativity
            max_output_tokens=1024,  # Reduced for faster responses
            timeout=30,  # 30 second timeout
            convert_system_message_to_human=True,  # Gemini compatibility
        )
        self.chat_history = InMemoryChatMessageHistory()
        
        # Create a prompt template that includes chat history
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are MaddyBot, a helpful AI assistant. Be friendly, concise, and direct. Keep responses brief unless detailed explanation is requested."),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ])

        # Lazy initialization of vectorstore (only when needed)
        self.embeddings = None
        self.vectorstore = None
        self.user_info_store = None  # Separate store for user information
        
        # Cache for user information (loaded once per session)
        self.user_info_cache = None
        self.user_info_loaded = False

        self.skills: Dict[str, object] = {
            "web_search": WebSearchSkill(),
            "code_runner": CodeRunnerSkill(),
            "time_tool": TimeTool(),
        }

    def _get_recent_history(self):
        """Get only recent messages to limit context size."""
        messages = self.chat_history.messages
        if len(messages) > self.max_history_messages:
            return messages[-self.max_history_messages:]
        return messages

    def _initialize_vectorstore(self):
        """Lazy initialization of vectorstore with Google embeddings."""
        if self.vectorstore is None:
            # Use Google's embeddings (faster and better quality)
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=self.api_key,
            )
            self.vectorstore = Chroma(
                collection_name="maddybot-memory",
                persist_directory=self.memory_path,
                embedding_function=self.embeddings,
            )
            # Initialize user info store
            self.user_info_store = Chroma(
                collection_name="maddybot-user-info",
                persist_directory=self.memory_path,
                embedding_function=self.embeddings,
            )

    def _load_user_info(self):
        """Load user information from persistent storage."""
        if self.user_info_loaded:
            return self.user_info_cache
        
        self.user_info_cache = {}
        try:
            self._initialize_vectorstore()
            if self.user_info_store:
                # Search for user information documents
                results = self.user_info_store.similarity_search("user name information", k=5)
                for doc in results:
                    # Parse user info from document content
                    content = doc.page_content
                    if "name:" in content.lower():
                        for line in content.split("\n"):
                            if "name:" in line.lower():
                                name = line.split(":", 1)[1].strip()
                                if name:
                                    self.user_info_cache["name"] = name
                                    break
        except Exception as e:
            print(f"Warning: Could not load user info: {e}")
        
        self.user_info_loaded = True
        return self.user_info_cache
    
    def _extract_user_info(self, message: str) -> Dict[str, str]:
        """Extract user information from message (name, preferences, etc.)."""
        info = {}
        message_lower = message.lower()
        
        # Extract name patterns - handle multi-word names
        name_patterns = [
            r"(?:my name is|i am|i'm|call me|save my name as|remember my name as)\s+([A-Za-z\s]+?)(?:\s|$|\.|,|!)",
            r"(?:name is|name's)\s+([A-Za-z\s]+?)(?:\s|$|\.|,|!)",
        ]
        
        import re
        for pattern in name_patterns:
            match = re.search(pattern, message_lower)
            if match:
                # Get the original case from the message
                start_pos = message_lower.find(match.group(0))
                if start_pos != -1:
                    name_part = message[start_pos + len(match.group(0).split()[-1]):]
                    # Extract just the name part
                    name_match = re.search(r"([A-Za-z]+(?:\s+[A-Za-z]+)*)", name_part)
                    if name_match:
                        name = name_match.group(1).strip()
                        if len(name) > 1:
                            info["name"] = name
                            break
        
        # Fallback: simpler extraction (handles "save my name as Maadhu")
        if not info.get("name"):
            # Try to find name after common phrases
            phrases = ["save my name as", "remember my name as", "my name is", "i am", "i'm", "call me"]
            for phrase in phrases:
                if phrase in message_lower:
                    idx = message_lower.find(phrase) + len(phrase)
                    remaining = message[idx:].strip()
                    # Extract first word or words (up to 3 words for names like "John Smith")
                    name_match = re.match(r"^([A-Za-z]+(?:\s+[A-Za-z]+){0,2})", remaining)
                    if name_match:
                        name = name_match.group(1).strip()
                        if len(name) > 1:
                            info["name"] = name
                            break
        
        return info
    
    def _store_user_info(self, info: Dict[str, str]):
        """Store user information persistently."""
        if not info:
            return
        
        try:
            self._initialize_vectorstore()
            if self.user_info_store:
                # Create document with user info
                content_parts = []
                for key, value in info.items():
                    content_parts.append(f"{key}: {value}")
                
                document = Document(
                    page_content="\n".join(content_parts),
                    metadata={
                        "type": "user_info",
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
                self.user_info_store.add_documents([document])
                # Update cache
                self.user_info_cache.update(info)
                print(f"Stored user info: {info}")
        except Exception as e:
            print(f"Warning: Could not store user info: {e}")

    def _retrieve_relevant_memory(self, query: str, k: int = 3) -> str:
        """Retrieve relevant past conversations from vectorstore."""
        try:
            self._initialize_vectorstore()
            if self.vectorstore is None:
                return ""
            
            # Search for relevant past conversations
            results = self.vectorstore.similarity_search(query, k=k)
            if not results:
                return ""
            
            # Format retrieved memories
            memory_parts = []
            for doc in results:
                memory_parts.append(doc.page_content)
            
            return "\n\n--- Relevant Past Conversations ---\n" + "\n\n---\n".join(memory_parts)
        except Exception as e:
            print(f"Warning: Could not retrieve memory: {e}")
            return ""

    def process_message(self, message: str) -> str:
        """Generate a reply using LangChain and update persistent memory."""
        try:
            # Load user information
            user_info = self._load_user_info()
            
            # Extract new user information from message
            extracted_info = self._extract_user_info(message)
            if extracted_info:
                self._store_user_info(extracted_info)
                user_info.update(extracted_info)
            
            # Retrieve relevant past conversations from database
            relevant_memory = self._retrieve_relevant_memory(message, k=2)
            
            # Build system message with user info
            system_message = "You are MaddyBot, a helpful AI assistant. Be friendly, concise, and direct. Keep responses brief unless detailed explanation is requested."
            if user_info.get("name"):
                system_message += f"\n\nIMPORTANT: The user's name is {user_info['name']}. Always use this name when addressing them. Remember this name for future conversations."
            
            if relevant_memory:
                system_message += f"\n\n{relevant_memory}"
            
            # Get only recent history to reduce context size
            recent_history = self._get_recent_history()
            
            # Create prompt with user info and memory
            prompt_with_info = ChatPromptTemplate.from_messages([
                ("system", system_message),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}"),
            ])
            
            # Build the chain with limited history
            chain = (
                RunnablePassthrough.assign(
                    history=lambda _: recent_history
                )
                | prompt_with_info
                | self.llm
            )
            
            # Invoke the conversation chain (timeout handled by LLM)
            response = chain.invoke({"input": message})
            
            # Extract the reply text
            reply = response.content if hasattr(response, 'content') else str(response)
            
            if not reply or reply.strip() == "":
                reply = "I'm sorry, I couldn't generate a response. Please try again."
            
            # Update chat history after getting response
            self.chat_history.add_message(HumanMessage(content=message))
            self.chat_history.add_message(AIMessage(content=reply))
            
            # Limit history size to prevent it from growing too large
            messages = self.chat_history.messages
            if len(messages) > self.max_history_messages:
                # Keep only the most recent messages
                self.chat_history.messages = messages[-self.max_history_messages:]

            # Store interaction in background (non-blocking, lazy init)
            import threading
            def store_async():
                try:
                    self._initialize_vectorstore()
                    if self.vectorstore:
                        self._store_interaction(message, reply)
                except Exception as e:
                    print(f"Warning: Could not store interaction in vectorstore: {e}")
            
            # Start storage in background thread
            thread = threading.Thread(target=store_async, daemon=True)
            thread.start()
            
            return reply
        except Exception as e:
            error_msg = str(e)
            print(f"Error in process_message: {error_msg}")
            raise Exception(f"Failed to process message: {error_msg}")

    def _store_interaction(self, user_message: str, assistant_reply: str) -> None:
        """Persist the latest exchange to Chroma for future long-term recall."""
        if self.vectorstore is None:
            return
        try:
            timestamp = datetime.utcnow().isoformat()
            document = Document(
                page_content=f"User: {user_message}\nAssistant: {assistant_reply}",
                metadata={
                    "timestamp": timestamp,
                    "model": self.model_name,
                },
            )
            self.vectorstore.add_documents([document])
            # Note: persist() is deprecated in newer Chroma versions - persistence is automatic
        except Exception as e:
            print(f"Warning: Error storing interaction: {e}")

    def process_message_with_media(self, message: str, images: list = None) -> str:
        """Generate a reply with media support (images, files, etc.)."""
        try:
            # Load user information
            user_info = self._load_user_info()
            
            # Extract new user information from message
            extracted_info = self._extract_user_info(message)
            if extracted_info:
                self._store_user_info(extracted_info)
                user_info.update(extracted_info)
            
            # Retrieve relevant past conversations from database
            relevant_memory = self._retrieve_relevant_memory(message, k=2)
            
            # Build system message with user info
            system_message = "You are MaddyBot, a helpful AI assistant. Be friendly, concise, and direct. Keep responses brief unless detailed explanation is requested."
            if user_info.get("name"):
                system_message += f"\n\nIMPORTANT: The user's name is {user_info['name']}. Always use this name when addressing them. Remember this name for future conversations."
            
            if relevant_memory:
                system_message += f"\n\n{relevant_memory}"
            
            # Gemini supports vision! Use gemini-pro-vision for images
            if images and len(images) > 0:
                try:
                    # Try to use vision model (gemini-2.5-flash supports vision)
                    vision_llm = ChatGoogleGenerativeAI(
                        model="gemini-2.5-flash",
                        google_api_key=self.api_key,
                        temperature=0.7,
                        max_output_tokens=1024,  # Reduced for faster responses
                        timeout=30,  # 30 second timeout
                    )
                    
                    # Build messages with images
                    from langchain_core.messages import HumanMessage, SystemMessage
                    vision_messages = []
                    
                    # Add system message with user info at the start
                    if user_info.get("name"):
                        vision_messages.append(SystemMessage(content=system_message))
                    
                    # Add history
                    recent_history = self._get_recent_history()
                    vision_messages.extend(recent_history)
                    
                    # Prepare image content for Gemini
                    import base64
                    
                    image_parts = []
                    for img_data in images:
                        if img_data.get("base64"):
                            # Decode base64 and create image part
                            image_bytes = base64.b64decode(img_data["base64"])
                            image_parts.append({
                                "mime_type": "image/jpeg",
                                "data": image_bytes
                            })
                    
                    # Create message with text and images
                    # Gemini expects content as a list with text and image parts
                    content_parts = []
                    if message:
                        content_parts.append(message)
                    content_parts.extend(image_parts)
                    
                    vision_messages.append(HumanMessage(content=content_parts))
                    
                    # Get response from vision model
                    response = vision_llm.invoke(vision_messages)
                    reply = response.content if hasattr(response, 'content') else str(response)
                    
                    # Update history
                    self.chat_history.add_message(HumanMessage(content=message or "[Image(s) attached]"))
                    self.chat_history.add_message(AIMessage(content=reply))
                    
                    # Store interaction
                    import threading
                    def store_async():
                        try:
                            self._initialize_vectorstore()
                            if self.vectorstore:
                                self._store_interaction(message or "[Image(s)]", reply)
                        except Exception as e:
                            print(f"Warning: Could not store interaction: {e}")
                    
                    thread = threading.Thread(target=store_async, daemon=True)
                    thread.start()
                    
                    return reply
                    
                except Exception as vision_error:
                    print(f"Vision model error, falling back to text: {vision_error}")
                    # Fall back to regular processing
                    if images:
                        message = f"[User attached {len(images)} image(s). Analyzing text content...]\n\n{message}"
                    return self.process_message(message)
            else:
                # No images, use regular processing
                return self.process_message(message)
        except Exception as e:
            error_msg = str(e)
            print(f"Error in process_message_with_media: {error_msg}")
            raise Exception(f"Failed to process message with media: {error_msg}")

    def get_skill(self, name: str) -> Optional[object]:
        return self.skills.get(name)
