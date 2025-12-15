const { createApp } = Vue;

createApp({
    data() {
        return {
            messages: [],
            userInput: '',
            isLoading: false,
            activeNav: 'newChat',
            API_URL: '/chat'
        };
    },
    mounted() {
        this.configureMarked();
    },
    methods: {
        configureMarked() {
            marked.setOptions({
                highlight: function(code, lang) {
                    const language = hljs.getLanguage(lang) ? lang : 'plaintext';
                    return hljs.highlight(code, { language }).value;
                },
                langPrefix: 'hljs language-',
                breaks: true,
                gfm: true
            });
        },
        
        parseMarkdown(text) {
            return marked.parse(text);
        },
        
        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        },
        
        async handleSend() {
            const text = this.userInput.trim();
            if (!text || this.isLoading) return;

            // Add user message
            this.messages.push({
                text: text,
                isUser: true
            });
            
            this.userInput = '';
            this.$nextTick(() => {
                this.resetTextareaHeight();
                this.scrollToBottom();
            });

            // Show loading
            this.isLoading = true;

            try {
                const response = await fetch(this.API_URL, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: text }),
                });

                const contentType = response.headers.get('content-type') || '';
                const isJson = contentType.includes('application/json');
                const payload = isJson ? await response.json() : await response.text();

                if (!response.ok) {
                    const detail = isJson ? (payload.detail || JSON.stringify(payload)) : String(payload);
                    throw new Error(`HTTP ${response.status}: ${detail}`);
                }

                const data = payload;
                
                // Add bot response
                this.messages.push({
                    text: data.response,
                    isUser: false
                });

            } catch (error) {
                console.error('Error:', error);
                this.messages.push({
                    text: `喵呜... 我这边遇到点问题：\n\n${String(error.message || error)}`,
                    isUser: false
                });
            } finally {
                this.isLoading = false;
                this.$nextTick(() => {
                    this.scrollToBottom();
                });
            }
        },
        
        autoResize(event) {
            const textarea = event.target;
            textarea.style.height = 'auto';
            textarea.style.height = textarea.scrollHeight + 'px';
        },
        
        resetTextareaHeight() {
            if (this.$refs.textarea) {
                this.$refs.textarea.style.height = 'auto';
            }
        },
        
        scrollToBottom() {
            if (this.$refs.chatContainer) {
                this.$refs.chatContainer.scrollTop = this.$refs.chatContainer.scrollHeight;
            }
        },
        
        handleNewChat() {
            this.messages = [];
            this.activeNav = 'newChat';
        },
        
        handleClearChat() {
            if (confirm('确定要清空当前对话吗？喵？')) {
                this.messages = [];
            }
        },
        
        handleHistory() {
            alert('历史记录功能开发中... 喵！');
            this.activeNav = 'history';
        },
        
        handleSettings() {
            alert('设置功能开发中... 喵！');
            this.activeNav = 'settings';
        }
    },
    watch: {
        messages: {
            handler() {
                this.$nextTick(() => {
                    this.scrollToBottom();
                });
            },
            deep: true
        }
    }
}).mount('#app');
