# Changelog - WebSocket Dynamic Language Support

## [2024-01-15] - Dynamic Language Selection Feature

### Added

- **Dynamic Language Selection via Query Parameter**
  - WebSocket connections now accept `lang` query parameter
  - Example: `wss://api.com/audio-stream?lang=it`
  - Supports 29 languages from Deepgram Nova-2
  - Defaults to English (`en`) if not specified or invalid

- **Language Constants**
  - `SUPPORTED_LANGUAGES`: List of 29 supported language codes
  - `DEFAULT_LANGUAGE`: Fallback language (`en`)

- **Enhanced Connection Response**
  - Server now confirms selected language in `connected` event
  - Response includes: `{'language': 'it', 'user_id': '...', ...}`

- **Comprehensive Logging**
  - Language selection logged for each connection
  - Invalid language attempts logged with warning
  - Deepgram connection includes language info

### Modified

- **`flask_app/sockets/audio_stream_auth0.py`**
  - Updated module docstring with feature description
  - Added language validation logic in `handle_connect()`
  - Language stored in `active_connections[sid]['language']`
  - Deepgram `LiveOptions` now uses dynamic `language` parameter
  - Enhanced logging with language information

### Documentation

- **WEBSOCKET_LANGUAGE_SUPPORT.md** (NEW)
  - Complete guide for using dynamic language selection
  - 29 supported languages with language codes
  - JavaScript/TypeScript examples
  - Python client examples
  - React Native examples
  - React component example
  - Architecture documentation
  - Testing guide

- **README.md**
  - Added WebSocket section with real-time transcription info
  - Linked to detailed language support documentation

- **examples/websocket_language_example.js** (NEW)
  - Comprehensive JavaScript/TypeScript examples
  - `AudioStreamClient` class for easy integration
  - 4 complete usage examples:
    1. Basic usage
    2. Microphone streaming
    3. Language selector UI
    4. React component
  
- **tests/test_websocket_language.py** (NEW)
  - Automated test script for language selection
  - Tests 6 scenarios (valid languages, invalid, missing)
  - Audio streaming test with language parameter
  - CLI tool with `--mode` and `--lang` options

### Technical Details

#### Language Validation Flow

```python
1. Extract: requested_lang = request.args.get('lang', 'en')
2. Validate: if requested_lang not in SUPPORTED_LANGUAGES
3. Default: language = 'en' if invalid
4. Store: active_connections[sid]['language'] = language
5. Configure: LiveOptions(language=language)
6. Confirm: emit('connected', {'language': language})
```

#### Supported Languages (29)

| Code | Language | Code | Language | Code | Language |
|------|----------|------|----------|------|----------|
| en | English | es | Spanish | fr | French |
| it | Italian | de | German | pt | Portuguese |
| nl | Dutch | hi | Hindi | ja | Japanese |
| ko | Korean | zh | Chinese | sv | Swedish |
| no | Norwegian | da | Danish | fi | Finnish |
| pl | Polish | ru | Russian | tr | Turkish |
| ar | Arabic | el | Greek | he | Hebrew |
| cs | Czech | uk | Ukrainian | ro | Romanian |
| hu | Hungarian | id | Indonesian | ms | Malay |
| th | Thai | vi | Vietnamese | | |

### Security

- ✅ Authentication still required (Auth0 JWT or session token)
- ✅ Language parameter validated against whitelist
- ✅ No injection vulnerabilities (enum validation)
- ✅ Auth token not stored in session (security improvement)

### Backward Compatibility

- ✅ **Fully backward compatible**
- ✅ Existing connections without `lang` parameter default to English
- ✅ No breaking changes to existing API
- ✅ All existing WebSocket events unchanged

### Migration Guide

**Before (hardcoded Italian):**
```javascript
const socket = io('wss://api.com/audio-stream', {
  auth: { token: authToken }
});
// Always transcribed in Italian
```

**After (dynamic language):**
```javascript
const socket = io('wss://api.com/audio-stream', {
  auth: { token: authToken },
  query: { lang: 'it' }  // ← Specify language
});
// Transcribes in specified language
```

### Performance Impact

- ⚡ **Negligible overhead**: Single dictionary lookup
- ⚡ **No additional API calls**: Language set once at connection
- ⚡ **Same Deepgram performance**: No latency increase

### Testing

Run automated tests:
```bash
# Install dependencies
pip install python-socketio

# Test language selection
python tests/test_websocket_language.py --token "YOUR_TOKEN" --mode language

# Test audio streaming
python tests/test_websocket_language.py --token "YOUR_TOKEN" --mode audio --lang it
```

### Future Enhancements

- [ ] Language auto-detection from audio
- [ ] Mid-session language switching
- [ ] Dialect support (e.g., en-US, en-GB)
- [ ] Language-specific formatting rules
- [ ] Translation alongside transcription

### Commit Information

- **Branch**: `auth0-add`
- **Files Changed**: 4 new, 2 modified
- **Lines Added**: ~1,200
- **Lines Removed**: ~10
- **Tests**: Manual testing completed, automated test suite added

### References

- [Deepgram Nova-2 Languages](https://developers.deepgram.com/docs/languages)
- [Socket.IO Query Parameters](https://socket.io/docs/v4/client-api/#socketquery)
- [Flask Request Context](https://flask.palletsprojects.com/en/3.0.x/reqcontext/)
