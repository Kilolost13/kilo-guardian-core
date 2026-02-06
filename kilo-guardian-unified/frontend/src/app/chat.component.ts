import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ChatService } from './services/chat.service';

@Component({
    selector: 'app-chat',
    standalone: true,
    imports: [CommonModule, FormsModule],
    template: `
    <div class="chat-container border border-gray-800 bg-black/50 p-4">
      <div class="chat-header flex items-center justify-between mb-2">
        <div class="text-[#39ff14] font-bold">AI Chat</div>
      </div>
      <div class="chat-body mb-3">
        <textarea [(ngModel)]="query" rows="3" placeholder="Ask something..." class="w-full p-2 bg-[#0a0a0a] text-white border border-gray-700 rounded"></textarea>
      </div>
      <div class="chat-actions flex justify-end gap-2">
        <button (click)="send()" class="bg-[#39ff14] text-black px-4 py-2 rounded">Send</button>
      </div>
      <div class="chat-response mt-3 text-sm whitespace-pre-wrap text-gray-300">
        <div *ngIf="isLoading">Processing...</div>
        <div *ngIf="error" class="text-red-500">{{error}}</div>
        <div *ngIf="response">
          <div *ngIf="isString(response)"> {{ response }} </div>
          <pre *ngIf="!isString(response)" style="font-family: monospace; font-size: 12px;">{{ formatJson(response) }}</pre>
        </div>
      </div>
    </div>
  `,
})
export class ChatComponent {
    query = '';
    response: any = null;
    isLoading = false;
    error: string | null = null;

    constructor(private chatSvc: ChatService) { }

    isString(v: any): boolean {
        return typeof v === 'string';
    }

    formatJson(obj: any): string {
        try { return JSON.stringify(obj, null, 2); } catch { return String(obj); }
    }

    send() {
        if (!this.query.trim()) return;
        this.isLoading = true;
        this.error = null;
        this.response = null;
        this.chatSvc.sendQuery(this.query.trim()).subscribe({
            next: (r) => { this.response = r; this.isLoading = false; },
            error: (err) => { this.error = err?.message || String(err); this.isLoading = false; }
        });
    }
}
