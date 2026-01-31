import api from './api';

export const chatService = {
  sendMessage: async (message: string): Promise<string> => {
    const response = await api.post('/ai_brain/chat', {
      message,
      user: 'kyle'
    });
    return response.data.response;
  },

  sendVoice: async (audioBlob: Blob): Promise<string> => {
    const formData = new FormData();
    formData.append('audio', audioBlob);
    const response = await api.post('/ai_brain/chat/voice', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data.text;
  },

  uploadImage: async (imageBlob: Blob, type: string): Promise<import('../types').UploadImageResult> => {
    const formData = new FormData();
    formData.append('image', imageBlob);
    formData.append('type', type);
    const response = await api.post('/ai_brain/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data as import('../types').UploadImageResult;
  },
};
