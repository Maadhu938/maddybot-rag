const form = document.getElementById("chat-form");
const input = document.getElementById("user-input");
const transcript = document.getElementById("chat-transcript");
const status = document.getElementById("status-indicator");
const fileUpload = document.getElementById("file-upload");
const imageUpload = document.getElementById("image-upload");
const voiceRecordBtn = document.getElementById("voice-record-btn");
const listeningIndicator = document.getElementById("listening-indicator");
const uploadPreview = document.getElementById("upload-preview");

let selectedFiles = [];
let selectedImages = [];
let isListening = false;
let recognition = null;

// Initialize Web Speech API
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = 'en-US';
  
  recognition.onstart = () => {
    isListening = true;
    voiceRecordBtn.classList.add('listening');
    listeningIndicator.style.display = 'flex';
  };
  
  let finalTranscript = '';
  
  recognition.onresult = (event) => {
    let interimTranscript = '';
    finalTranscript = '';
    
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalTranscript += transcript;
      } else {
        interimTranscript += transcript;
      }
    }
    
    // Update input field with both interim and final results
    input.value = finalTranscript + interimTranscript;
  };
  
  recognition.onend = () => {
    isListening = false;
    voiceRecordBtn.classList.remove('listening');
    listeningIndicator.style.display = 'none';
    
    // Get final transcript and send if available
    const transcriptToSend = input.value.trim();
    if (transcriptToSend) {
      // Show user message
      appendMessage("You", transcriptToSend, true);
      input.value = '';
      // Send the message
      sendMessage(transcriptToSend).catch((error) => {
        console.error(error);
        appendMessage("MaddyBot", "Something went wrong while reaching the model.");
      });
    }
  };
  
  recognition.onerror = (event) => {
    console.error('Speech recognition error:', event.error);
    isListening = false;
    voiceRecordBtn.classList.remove('listening');
    listeningIndicator.style.display = 'none';
    
    let errorMsg = 'Speech recognition error. ';
    if (event.error === 'no-speech') {
      errorMsg = 'No speech detected. Please try again.';
    } else if (event.error === 'not-allowed') {
      errorMsg = 'Microphone permission denied. Please allow microphone access.';
    }
    appendMessage("MaddyBot", errorMsg);
  };
} else {
  // Browser doesn't support speech recognition
  voiceRecordBtn.style.display = 'none';
  console.warn('Speech recognition not supported in this browser');
}

// Markdown parser
function parseMarkdown(text) {
  if (!text) return "";
  
  let html = text;
  
  // Escape HTML first
  html = html.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  
  // Code blocks with language
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
    const language = lang || "";
    return `<pre><code class="language-${language}">${code.trim()}</code></pre>`;
  });
  
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  // Headers
  html = html.replace(/^### (.*$)/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.*$)/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.*$)/gm, "<h1>$1</h1>");
  
  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/__(.+?)__/g, "<strong>$1</strong>");
  
  // Italic
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
  html = html.replace(/_(.+?)_/g, "<em>$1</em>");
  
  // Links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  
  // Lists
  html = html.replace(/^\* (.+)$/gm, "<li>$1</li>");
  html = html.replace(/^- (.+)$/gm, "<li>$1</li>");
  html = html.replace(/^\+ (.+)$/gm, "<li>$1</li>");
  
  // Wrap consecutive list items in ul
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => {
    return `<ul>${match}</ul>`;
  });
  
  // Numbered lists
  html = html.replace(/^\d+\. (.+)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => {
    if (match.includes("<ul>")) return match;
    return `<ol>${match}</ol>`;
  });
  
  // Blockquotes
  html = html.replace(/^> (.+)$/gm, "<blockquote>$1</blockquote>");
  
  // Horizontal rule
  html = html.replace(/^---$/gm, "<hr>");
  html = html.replace(/^\*\*\*$/gm, "<hr>");
  
  // Paragraphs (split by double newlines)
  html = html.split(/\n\n+/).map(para => {
    para = para.trim();
    if (!para) return "";
    // Don't wrap if it's already a block element
    if (/^<(h[1-6]|ul|ol|pre|blockquote|hr)/.test(para)) {
      return para;
    }
    return `<p>${para}</p>`;
  }).join("\n");
  
  // Line breaks
  html = html.replace(/\n/g, "<br>");
  
  return html;
}

function appendMessage(author, text, isUser = false, attachments = null) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${isUser ? "user" : "bot"}`;

  const name = document.createElement("span");
  name.className = "author";
  name.textContent = author;

  const body = document.createElement("div");
  body.className = "text";
  
  // Add attachments if any
  if (attachments) {
    if (attachments.images && attachments.images.length > 0) {
      attachments.images.forEach(img => {
        // Create image preview from file if available, or use base64 if provided
        if (img.file) {
          // Create preview from File object
          const reader = new FileReader();
          reader.onload = (e) => {
            const imgEl = document.createElement("img");
            imgEl.src = e.target.result;
            imgEl.style.maxWidth = "300px";
            imgEl.style.borderRadius = "8px";
            imgEl.style.margin = "8px 0";
            imgEl.alt = img.name || "Uploaded image";
            body.appendChild(imgEl);
          };
          reader.readAsDataURL(img.file);
        } else if (img.base64) {
          // Use base64 data if available
          const imgEl = document.createElement("img");
          imgEl.src = `data:image/jpeg;base64,${img.base64}`;
          imgEl.style.maxWidth = "300px";
          imgEl.style.borderRadius = "8px";
          imgEl.style.margin = "8px 0";
          imgEl.alt = img.name || "Uploaded image";
          imgEl.onerror = () => {
            // Fallback if image fails to load
            const errorDiv = document.createElement("div");
            errorDiv.textContent = `🖼️ ${img.name || "Image"}`;
            errorDiv.style.cssText = "padding: 8px; background: rgba(255,0,0,0.1); border-radius: 4px; margin: 4px 0; color: #ff6b6b;";
            body.appendChild(errorDiv);
          };
          body.appendChild(imgEl);
        } else {
          // Just show file name if no image data
          const fileDiv = document.createElement("div");
          fileDiv.textContent = `🖼️ ${img.name || "Image"}`;
          fileDiv.style.cssText = "padding: 8px; background: rgba(0,0,0,0.2); border-radius: 4px; margin: 4px 0;";
          body.appendChild(fileDiv);
        }
      });
    }
    if (attachments.files && attachments.files.length > 0) {
      attachments.files.forEach(file => {
        const fileEl = document.createElement("div");
        fileEl.style.cssText = "padding: 8px; background: rgba(0,0,0,0.2); border-radius: 4px; margin: 4px 0;";
        fileEl.textContent = `📄 ${file.name}`;
        body.appendChild(fileEl);
      });
    }
    if (attachments.audio) {
      const audioEl = document.createElement("div");
      audioEl.style.cssText = "padding: 8px; background: rgba(0,0,0,0.2); border-radius: 4px; margin: 4px 0;";
      audioEl.textContent = `🎤 Audio: ${attachments.audio.name || "Audio file"}`;
      body.appendChild(audioEl);
    }
  }
  
  body.innerHTML += parseMarkdown(text);

  wrapper.appendChild(name);
  wrapper.appendChild(body);
  transcript.appendChild(wrapper);
  
  // Remove empty state if exists
  const emptyState = transcript.querySelector(".empty-state");
  if (emptyState) {
    emptyState.remove();
  }
  
  scrollToBottom();
}

function showTypingIndicator() {
  const wrapper = document.createElement("div");
  wrapper.className = "message bot";
  wrapper.id = "typing-indicator";

  const name = document.createElement("span");
  name.className = "author";
  name.textContent = "MaddyBot";

  const indicator = document.createElement("div");
  indicator.className = "typing-indicator";
  indicator.innerHTML = "<span></span><span></span><span></span>";

  wrapper.appendChild(name);
  wrapper.appendChild(indicator);
  transcript.appendChild(wrapper);
  scrollToBottom();
}

function removeTypingIndicator() {
  const indicator = document.getElementById("typing-indicator");
  if (indicator) {
    indicator.remove();
  }
}

function scrollToBottom() {
  transcript.scrollTop = transcript.scrollHeight;
}

function showEmptyState() {
  if (transcript.children.length === 0) {
    const emptyState = document.createElement("div");
    emptyState.className = "empty-state";
    emptyState.innerHTML = `
      <h2>👋 Welcome to MaddyBot 2.0</h2>
      <p>Start a conversation by typing a message below</p>
    `;
    transcript.appendChild(emptyState);
  }
}

function updateUploadPreview() {
  uploadPreview.innerHTML = "";
  
  const hasAttachments = selectedFiles.length > 0 || selectedImages.length > 0;
  
  if (!hasAttachments) {
    uploadPreview.style.display = "none";
    return;
  }
  
  uploadPreview.style.display = "block";
  
  selectedFiles.forEach((file, idx) => {
    const chip = document.createElement("div");
    chip.className = "upload-chip";
    chip.innerHTML = `
      <span>📄 ${file.name}</span>
      <button onclick="removeFile(${idx})" type="button">×</button>
    `;
    uploadPreview.appendChild(chip);
  });
  
  selectedImages.forEach((img, idx) => {
    const chip = document.createElement("div");
    chip.className = "upload-chip";
    chip.innerHTML = `
      <span>🖼️ ${img.name}</span>
      <button onclick="removeImage(${idx})" type="button">×</button>
    `;
    uploadPreview.appendChild(chip);
  });
}

window.removeFile = function(idx) {
  selectedFiles.splice(idx, 1);
  updateUploadPreview();
};

window.removeImage = function(idx) {
  selectedImages.splice(idx, 1);
  updateUploadPreview();
};

// Voice recording button handler
voiceRecordBtn.addEventListener('click', () => {
  if (!recognition) {
    appendMessage("MaddyBot", "Speech recognition is not supported in your browser.");
    return;
  }
  
  if (isListening) {
    recognition.stop();
  } else {
    input.value = '';
    recognition.start();
  }
});

// File upload handlers
fileUpload.addEventListener("change", (e) => {
  selectedFiles = Array.from(e.target.files);
  updateUploadPreview();
});

imageUpload.addEventListener("change", (e) => {
  selectedImages = Array.from(e.target.files);
  updateUploadPreview();
});

// Removed audio file upload handler - using voice recording instead

async function sendMessage(message) {
  status.textContent = "Thinking…";
  status.classList.add("active");
  
  input.disabled = true;
  form.querySelector("button[type='submit']").disabled = true;
  
  showTypingIndicator();

  try {
    const startTime = Date.now();
    let response;
    
    // Check if we have files to upload
    const hasAttachments = selectedFiles.length > 0 || selectedImages.length > 0;
    
    if (hasAttachments) {
      // Use FormData for file uploads
      const formData = new FormData();
      formData.append("message", message || "");
      
      selectedFiles.forEach(file => {
        formData.append("files", file);
      });
      
      selectedImages.forEach(img => {
        formData.append("images", img);
      });
      
      response = await fetch("/api/chat", {
        method: "POST",
        body: formData,
      });
    } else {
      // Regular JSON request (can include audio transcription)
      const requestData = { message };
      // Note: audio transcription is handled by voice recording and sent as message
      response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestData),
      });
    }

    removeTypingIndicator();
    status.textContent = "";
    status.classList.remove("active");

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      appendMessage("MaddyBot", errorData.reply || "I ran into an issue processing that message.");
      return;
    }

    const data = await response.json();
    const responseTime = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`Response time: ${responseTime}s`);
    
    // Show attachments in user message (include File objects for preview)
    const attachments = hasAttachments ? {
      files: selectedFiles.map(f => ({ name: f.name })),
      images: selectedImages.map(img => ({ name: img.name, file: img }))
    } : null;
    
    if (hasAttachments && message) {
      appendMessage("You", message, true, attachments);
    } else if (hasAttachments) {
      appendMessage("You", "[Sent files/images]", true, attachments);
    }
    
    appendMessage("MaddyBot", data.reply || "(no reply)");
    
    // Clear attachments after sending
    selectedFiles = [];
    selectedImages = [];
    fileUpload.value = "";
    imageUpload.value = "";
    updateUploadPreview();
    
  } catch (error) {
    removeTypingIndicator();
    status.textContent = "";
    status.classList.remove("active");
    console.error("Error:", error);
    appendMessage("MaddyBot", "Network error: Could not reach the server. Please check if the server is running.");
  } finally {
    input.disabled = false;
    form.querySelector("button[type='submit']").disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = input.value.trim();
  const hasAttachments = selectedFiles.length > 0 || selectedImages.length > 0;
  
  if (!message && !hasAttachments) {
    return;
  }

  if (message) {
    appendMessage("You", message, true);
  }
  
  input.value = "";
  sendMessage(message).catch((error) => {
    console.error(error);
    appendMessage("MaddyBot", "Something went wrong while reaching the model.");
  });
});

// Show empty state on load
showEmptyState();

// Auto-focus input
input.focus();
