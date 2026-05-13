document.addEventListener('DOMContentLoaded', () => {
    const messageList = document.getElementById('messageList');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');

    function showThinking() {
        const thinkingIndicator = document.getElementById('thinkingIndicator');
        thinkingIndicator.style.display = 'flex';
        messageList.appendChild(thinkingIndicator);
        messageList.scrollTo({ top: messageList.scrollHeight, behavior: 'smooth' });
    }

    function hideThinking() {
        const thinkingIndicator = document.getElementById('thinkingIndicator');
        thinkingIndicator.style.display = 'none';
    }

    function addMessage(text, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', `${sender}-msg`);
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.classList.add('bubble');
        
        if (sender === 'jinu' && typeof marked !== 'undefined') {
            bubbleDiv.innerHTML = marked.parse(text);
        } else {
            bubbleDiv.textContent = text;
        }
        
        msgDiv.appendChild(bubbleDiv);
        messageList.appendChild(msgDiv);
        
        const thinkingIndicator = document.getElementById('thinkingIndicator');
        if (thinkingIndicator && thinkingIndicator.style.display !== 'none') {
            messageList.appendChild(thinkingIndicator);
        }
        
        // Smooth scroll to bottom
        messageList.scrollTo({ top: messageList.scrollHeight, behavior: 'smooth' });
    }

    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        // Add user message to UI
        addMessage(text, 'user');
        userInput.value = '';
        showThinking();

        try {
            // Send to FastAPI backend
            const response = await fetch('http://127.0.0.1:8000/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: text })
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            hideThinking();
            
            // Add JINU's reply to UI
            addMessage(data.reply, 'jinu');
        } catch (error) {
            console.error('Error:', error);
            hideThinking();
            addMessage('Error: Could not connect to JINU brain.', 'jinu');
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Mute Button Logic
    const muteBtn = document.getElementById('muteBtn');
    muteBtn.addEventListener('click', async () => {
        try {
            const res = await fetch('http://127.0.0.1:8000/toggle_mute', { method: 'POST' });
            const data = await res.json();
            if (data.muted) {
                muteBtn.style.color = '#ff4444'; // Red when muted
            } else {
                muteBtn.style.color = 'inherit';
            }
        } catch (e) {
            console.error('Error toggling mute', e);
        }
    });

    // Mic Button Logic
    const micBtn = document.getElementById('micBtn');
    micBtn.addEventListener('click', async () => {
        micBtn.style.color = '#44ff44'; // Green while listening
        userInput.placeholder = "Listening...";
        userInput.disabled = true;

        try {
            const res = await fetch('http://127.0.0.1:8000/listen', { method: 'POST' });
            const data = await res.json();
            
            if (data.text) {
                userInput.value = data.text;
                sendMessage();
            } else if (data.error) {
                addMessage('JINU: ' + data.error, 'jinu');
            }
        } catch (e) {
            console.error('Error listening', e);
        } finally {
            micBtn.style.color = 'inherit';
            userInput.placeholder = "Type a message...";
            userInput.disabled = false;
        }
    });

    // Listen for proactive messages from JINU via Server-Sent Events
    const eventSource = new EventSource('http://127.0.0.1:8000/stream');
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            if (data.reply) {
                addMessage(data.reply, 'jinu');
            }
        } catch (e) {
            console.error('Error parsing SSE event:', e);
        }
    };
});
