const { createApp } = Vue;

createApp({
    data() {
        return {
            messages: [],
            userInput: '',
            isLoading: false,
            activeNav: 'newChat',
            API_URL: '/chat',
            userId: 'user_' + Math.random().toString(36).substring(2, 11),
            sessionId: 'session_' + Date.now(),
            sessions: [],
            showHistorySidebar: false,
            isComposing: false,
            // 文档管理相关
            documents: [],
            documentsLoading: false,
            selectedFile: null,
            isUploading: false,
            uploadProgress: ''
        };
    },
    mounted() {
        this.configureMarked();
        // 尝试从 localStorage 恢复用户ID
        const savedUserId = localStorage.getItem('userId');
        if (savedUserId) {
            this.userId = savedUserId;
        } else {
            localStorage.setItem('userId', this.userId);
        }
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
        
        handleCompositionStart() {
            this.isComposing = true;
        },
        
        handleCompositionEnd() {
            this.isComposing = false;
        },
        
        handleKeyDown(event) {
            // 如果是回车键且不是Shift+回车，且不在输入法组合中
            if (event.key === 'Enter' && !event.shiftKey && !this.isComposing) {
                event.preventDefault();
                this.handleSend();
            }
        },
        
        async handleSend() {
            const text = this.userInput.trim();
            if (!text || this.isLoading || this.isComposing) return;

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
                    body: JSON.stringify({ 
                        message: text,
                        user_id: this.userId,
                        session_id: this.sessionId
                    }),
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
            this.sessionId = 'session_' + Date.now();
            this.activeNav = 'newChat';
            this.showHistorySidebar = false;
        },
        
        handleClearChat() {
            if (confirm('确定要清空当前对话吗？喵？')) {
                this.messages = [];
            }
        },
        
        async handleHistory() {
            this.activeNav = 'history';
            this.showHistorySidebar = true;
            try {
                const response = await fetch(`/sessions/${this.userId}`);
                if (!response.ok) {
                    throw new Error('Failed to load sessions');
                }
                const data = await response.json();
                this.sessions = data.sessions;
            } catch (error) {
                console.error('Error loading sessions:', error);
                alert('加载历史记录失败：' + error.message);
            }
        },
        
        async loadSession(sessionId) {
            this.sessionId = sessionId;
            this.showHistorySidebar = false;
            this.activeNav = 'newChat';
            
            // 从后端加载历史消息
            try {
                const response = await fetch(`/sessions/${this.userId}/${sessionId}`);
                if (!response.ok) {
                    throw new Error('Failed to load session messages');
                }
                const data = await response.json();
                
                // 转换消息格式并显示
                this.messages = data.messages.map(msg => ({
                    text: msg.content,
                    isUser: msg.type === 'human'
                }));
                
                this.$nextTick(() => {
                    this.scrollToBottom();
                });
            } catch (error) {
                console.error('Error loading session:', error);
                alert('加载会话失败：' + error.message);
                this.messages = [];
            }
        },
        
        handleSettings() {
            this.activeNav = 'settings';
            this.showHistorySidebar = false;
            // 加载文档列表
            this.loadDocuments();
        },
        
        async loadDocuments() {
            this.documentsLoading = true;
            try {
                const response = await fetch('/documents');
                if (!response.ok) {
                    throw new Error('Failed to load documents');
                }
                const data = await response.json();
                this.documents = data.documents;
            } catch (error) {
                console.error('Error loading documents:', error);
                alert('加载文档列表失败：' + error.message);
            } finally {
                this.documentsLoading = false;
            }
        },
        
        handleFileSelect(event) {
            const files = event.target.files;
            if (files && files.length > 0) {
                this.selectedFile = files[0];
                this.uploadProgress = '';
            }
        },
        
        async uploadDocument() {
            if (!this.selectedFile) {
                alert('请先选择文件');
                return;
            }
            
            this.isUploading = true;
            this.uploadProgress = '正在上传...';
            
            try {
                const formData = new FormData();
                formData.append('file', this.selectedFile);
                
                const response = await fetch('/documents/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Upload failed');
                }
                
                const data = await response.json();
                this.uploadProgress = data.message;
                
                // 清空选择
                this.selectedFile = null;
                if (this.$refs.fileInput) {
                    this.$refs.fileInput.value = '';
                }
                
                // 刷新文档列表
                await this.loadDocuments();
                
                // 3秒后清除提示
                setTimeout(() => {
                    this.uploadProgress = '';
                }, 3000);
                
            } catch (error) {
                console.error('Error uploading document:', error);
                this.uploadProgress = '上传失败：' + error.message;
            } finally {
                this.isUploading = false;
            }
        },
        
        async deleteDocument(filename) {
            if (!confirm(`确定要删除文档 "${filename}" 吗？这将同时删除 Milvus 中的所有相关向量。`)) {
                return;
            }
            
            try {
                const response = await fetch(`/documents/${encodeURIComponent(filename)}`, {
                    method: 'DELETE'
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Delete failed');
                }
                
                const data = await response.json();
                alert(data.message);
                
                // 刷新文档列表
                await this.loadDocuments();
                
            } catch (error) {
                console.error('Error deleting document:', error);
                alert('删除文档失败：' + error.message);
            }
        },
        
        getFileIcon(fileType) {
            if (fileType === 'PDF') {
                return 'fas fa-file-pdf';
            } else if (fileType === 'Word') {
                return 'fas fa-file-word';
            }
            return 'fas fa-file';
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
