# Voice Assistant Roadmap - "Kilo's Voice"

**Status:** Voice Input (STT) ✅ Implemented | Voice Output (TTS) 📋 Planned
**Priority:** Medium
**Estimated Timeline:** 2-3 weeks
**Complexity:** Medium

---

## Current State (December 2025)

### ✅ What's Working
- **Speech-to-Text (STT):** Browser-native Web Speech API
  - Uses `react-speech-recognition` library
  - Works on modern browsers (Chrome, Edge, Safari)
  - Converts user voice → text → sent to AI Brain
  - No server-side processing required (client-side only)

### ⚠️ Current Issues
1. **No Visual Feedback:** Mic icon doesn't show when listening/processing
2. **No Audio Levels:** Can't see if mic is picking up speech
3. **Error Handling:** Chat returns "sorry, I encountered an error" for voice inputs
4. **No Voice Output:** Kilo can't speak responses back to user

---

## Roadmap Overview

### Phase 1: Fix Voice Input Issues (1 week)
**Priority:** HIGH
**Goal:** Make existing voice input reliable and user-friendly

**Tasks:**
1. **Debug AI Brain Connection**
   - Investigate why voice inputs fail in chat
   - Check chatService.sendMessage() error handling
   - Add proper logging for voice requests
   - Test: voice input → transcription → AI response

2. **Add Visual Feedback**
   - Animated microphone icon when listening
   - Pulsing effect during speech detection
   - Audio level visualization (bar graph)
   - Status indicator: "Listening..." → "Processing..." → "Complete"

3. **Improve UX**
   - Add "Press to speak" hint
   - Show transcribed text before sending
   - Allow editing transcribed text before submission
   - Add voice input timeout (30 seconds max)

**Deliverables:**
- Voice input works reliably end-to-end
- Visual feedback shows listening/processing state
- User-friendly error messages
- Test coverage for voice flows

---

### Phase 2: Implement Text-to-Speech (2 weeks)
**Priority:** MEDIUM
**Goal:** Give Kilo a voice to speak responses

#### Option A: Browser Web Speech API (Recommended)
**Pros:**
- ✅ No server/API costs
- ✅ Works offline (air-gapped deployment)
- ✅ Built into modern browsers
- ✅ Multiple voice options
- ✅ Fast (no network latency)

**Cons:**
- ❌ Voice quality varies by browser
- ❌ Limited voice customization
- ❌ No consistent "Kilo personality" across devices

**Implementation:**
```typescript
// Add to frontend/src/services/ttsService.ts
const speak = (text: string) => {
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.voice = speechSynthesis.getVoices()[0]; // Select voice
  utterance.rate = 1.0;   // Speed
  utterance.pitch = 1.0;  // Pitch
  utterance.volume = 1.0; // Volume
  speechSynthesis.speak(utterance);
};
```

**Timeline:** 3-5 days

---

#### Option B: Server-Side TTS (gTTS/piper)
**Pros:**
- ✅ Consistent voice across devices
- ✅ Custom voice training possible
- ✅ Better quality (can use neural TTS)

**Cons:**
- ❌ Requires server resources
- ❌ Network latency
- ❌ May not work in air-gapped mode without pre-download

**Implementation:**
```python
# services/voice/main.py
from gtts import gTTS
import pyttsx3

@app.post("/tts")
def text_to_speech(text: str):
    tts = gTTS(text=text, lang='en')
    filename = f"/tmp/{uuid.uuid4()}.mp3"
    tts.save(filename)
    return FileResponse(filename, media_type="audio/mpeg")
```

**Timeline:** 1-2 weeks (includes voice service setup)

---

#### Option C: Hybrid Approach (Best of Both)
**Strategy:**
1. Use Browser TTS by default (fast, offline)
2. Optionally use server TTS for "important" responses
3. Allow user to toggle TTS provider in settings

**Timeline:** 2 weeks

**Recommendation:** **Start with Option A (Browser TTS)** for MVP, then add Option B later if needed.

---

### Phase 3: Voice Personality & Settings (3-5 days)
**Goal:** Make Kilo's voice feel like Kilo

**Tasks:**
1. **Voice Selection UI**
   - Settings page: choose from available voices
   - Preview voice samples
   - Save preference to localStorage

2. **Personality Tuning**
   - Adjust rate/pitch/volume for "Kilo's character"
   - Friendly, encouraging tone
   - Slight variations for different message types:
     - Reminders: Gentle, calm
     - Achievements: Excited, upbeat
     - Errors: Apologetic, helpful

3. **Smart TTS Triggers**
   - Auto-speak important notifications
   - Voice confirmation for actions ("Reminder saved!")
   - Don't speak every chat message (too annoying)
   - User can toggle "auto-speak" on/off

**Deliverables:**
- Settings UI for voice preferences
- Smart TTS triggers for key events
- Documented voice personality guidelines

---

### Phase 4: Advanced Features (Future)
**Priority:** LOW
**Timeline:** TBD

1. **Custom Voice Training**
   - Train a custom TTS model that sounds like "Kilo"
   - Use tools like Piper, Coqui TTS, or Tortoise
   - Requires: voice samples, GPU, time

2. **Conversation Mode**
   - Continuous voice interaction (no button press)
   - "Hey Kilo" wake word detection
   - Natural back-and-forth conversation

3. **Voice Commands**
   - "Kilo, add a reminder for..."
   - "Kilo, what's my balance?"
   - "Kilo, take a photo"
   - Intent recognition for actions

4. **Multilingual Support**
   - Spanish, French, etc.
   - Auto-detect language from speech

5. **Voice Analytics**
   - Track voice usage patterns
   - Mood detection from tone
   - Health insights from voice (cough detection, etc.)

---

## Technical Implementation Details

### Frontend Changes
**New Files:**
- `src/services/ttsService.ts` - Text-to-speech service
- `src/components/VoiceVisualizer.tsx` - Audio level visualizer
- `src/hooks/useVoiceInput.ts` - Voice input hook with feedback

**Modified Files:**
- `src/pages/Dashboard.tsx` - Add TTS for AI responses
- `src/components/shared/Button.tsx` - Add "Speak" button variant
- `src/services/chatService.ts` - Add TTS option to sendMessage

### Backend Changes (for Option B)
**New Service:**
- `services/voice/` - Dedicated TTS/STT service
  - Port: 9009 (already exists but minimal)
  - Endpoints: POST /tts, POST /stt
  - Dependencies: gTTS, pyttsx3, or piper

**Modified Files:**
- `services/ai_brain/main.py` - Add TTS audio file generation
- `infra/docker/docker-compose.yml` - Ensure voice service configured

---

## Research & Tools

### Browser APIs
- **Web Speech API:** https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API
- **SpeechSynthesis:** Text-to-speech
- **SpeechRecognition:** Speech-to-text (already using)

### Server-Side TTS Libraries
- **gTTS (Google TTS):** Simple, good quality, requires internet
- **pyttsx3:** Offline, platform-specific voices
- **Piper:** Fast neural TTS, runs locally, great quality
- **Coqui TTS:** Advanced neural TTS, trainable
- **Tortoise TTS:** High-quality but slow

### Voice Datasets (if training custom voice)
- **LJSpeech:** Public domain audiobook recordings
- **LibriTTS:** Multi-speaker dataset
- **Common Voice:** Mozilla's crowdsourced dataset

---

## Testing Plan

### Phase 1 Tests
- [ ] Voice input triggers correctly
- [ ] Visual feedback shows during listening
- [ ] Transcription appears in chat
- [ ] AI response generated successfully
- [ ] Error messages display clearly

### Phase 2 Tests
- [ ] TTS speaks AI responses
- [ ] Voice quality is acceptable
- [ ] Volume/rate/pitch adjustable
- [ ] Works on mobile browsers
- [ ] Works offline (for Browser API)

### Phase 3 Tests
- [ ] Voice settings save correctly
- [ ] Auto-speak triggers appropriately
- [ ] User can toggle TTS on/off
- [ ] Voice personality feels consistent

---

## Cost & Resource Estimates

### Development Time
- **Phase 1 (Fix Voice Input):** 1 week (1 developer)
- **Phase 2 (Implement TTS):** 2 weeks (1 developer)
- **Phase 3 (Personality & Settings):** 3-5 days (1 developer)
- **Total:** ~3-4 weeks

### Infrastructure Costs
- **Browser TTS (Option A):** $0 (client-side)
- **Server TTS (Option B):** ~$10-20/month (storage for audio files)
- **Custom Voice Training:** $100-500 (GPU time if using cloud)

### Ongoing Maintenance
- Minimal (Browser API is stable)
- Voice service monitoring if using server TTS
- Periodic voice quality improvements

---

## Success Metrics

1. **Voice Input Success Rate:** >95% of voice inputs transcribed correctly
2. **TTS Adoption:** >50% of users enable voice output
3. **Error Rate:** <5% of voice interactions fail
4. **User Satisfaction:** Positive feedback on voice quality
5. **Performance:** <500ms latency for TTS playback

---

## Risks & Mitigations

### Risk 1: Browser Compatibility
**Mitigation:** Feature detection, graceful degradation, show warning if unsupported

### Risk 2: Privacy Concerns
**Mitigation:** All processing client-side (Browser API), no voice data leaves device

### Risk 3: Noise/Accuracy Issues
**Mitigation:** Show transcribed text, allow editing before send

### Risk 4: Annoying Voice Output
**Mitigation:** Smart triggers, user control, easy mute option

---

## Next Steps

1. **Week 1:** Fix existing voice input issues (Phase 1)
2. **Week 2-3:** Implement Browser TTS (Phase 2, Option A)
3. **Week 4:** Add voice settings and personality (Phase 3)
4. **Future:** Evaluate need for advanced features (Phase 4)

**Owner:** Development Team
**Review Date:** January 2026
**Status Updates:** Weekly in team standup

---

**Last Updated:** December 28, 2025
**Document Version:** 1.0
**Next Review:** After Phase 1 completion
