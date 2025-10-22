# 🎯 YouTube Video Transcription Fixes

## ❌ **Problema Originale**

```text
ERROR: unable to download video data: HTTP Error 403: Forbidden
```

## ✅ **Soluzioni Implementate**

### **1. Configurazione yt-dlp Potenziata**

- **User Agent**: Simulazione di browser reale (Chrome 119)
- **Headers HTTP**: Headers completi per evitare detection
- **Retry Logic**: Tentativi multipli con backoff esponenziale
- **Formato Audio**: Specifiche migliorate per estrazione audio

### **2. Gestione Errori Migliorata**

- **Errori Specifici**: Messaggi diversi per 403, 404, e altri errori
- **Suggerimenti Automatici**: Consigli per risolvere problemi comuni
- **Fallback**: Indicazioni per upload diretto di file video

### **3. Aggiornamento Automatico**

- **Script**: `./scripts/update_ytdlp.sh` per aggiornare yt-dlp
- **Versione**: Aggiornato da 2024.11.4 a 2025.10.14
- **Compatibilità**: Supporto per restrizioni YouTube più recenti

### **4. Test e Debugging**

- **Script Test**: `test_video_fixes.py` per verificare funzionalità
- **Video Multipli**: Test con URL diversi per identificare pattern
- **Logging**: Messaggi di debug più dettagliati

---

## 🚀 **Come Testare le Fixes**

### **1. Aggiorna yt-dlp**

```bash
./scripts/update_ytdlp.sh
```

### **2. Testa con Video Semplici**

```bash
curl -X POST http://localhost:5000/transcriptions/video \
  -H "x-api-key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "model_size": "tiny"
  }'
```

### **3. Usa lo Script di Test**

```bash
# Modifica API key in test_video_fixes.py
python test_video_fixes.py
```

### **4. Fallback: Upload Diretto**

```bash
curl -X POST http://localhost:5000/transcriptions/video \
  -H "x-api-key: your-key" \
  -F "video=@your-video.mp4" \
  -F "model_size=tiny"
```

---

## 🔧 **Modifiche Tecniche**

### **VideoProcessor** (`flask_app/clients/video_processor.py`)

```python
# Enhanced yt-dlp options
ydl_opts = {
    'format': 'bestaudio/best',
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
    'headers': {
        'Accept': 'text/html,application/xhtml+xml...',
        'Accept-Language': 'en-us,en;q=0.5',
        # ... more headers
    },
    'extractor_retries': 3,
    'fragment_retries': 3,
    'retry_sleep_functions': {
        'http': lambda n: min(4 ** n, 60),
        # ... more retry logic
    }
}
```

### **Error Messages** (Enhanced)

```python
if "403" in error_msg or "Forbidden" in error_msg:
    raise TranscriptionError(
        "Video download blocked by YouTube. This can happen due to:\n"
        "1. Video has restricted access\n"
        "2. Geographic restrictions\n" 
        "3. YouTube's anti-bot measures\n"
        "4. Video requires login\n\n"
        "Try: Updating yt-dlp, using a different video, or uploading the video file directly."
    )
```

---

## 🎯 **Risultati Attesi**

### **✅ Dovrebbero Funzionare**

- Video pubblici senza restrizioni
- Video educativi/musicali standard
- Video con audio chiaro e accessibile

### **⚠️ Potrebbero Fallire Ancora**

- Video con restrizioni geografiche
- Video che richiedono login
- Video age-restricted
- Video con protezioni specifiche dell'uploader

### **🔄 Alternative Sempre Disponibili**

- Upload diretto di file video
- Conversione locale video → audio → upload
- Uso di altri servizi di transcription per video problematici

---

## 📊 **Monitoraggio**

Il sistema ora logga:
- **Successi**: Conferma download e transcription
- **Errori Specifici**: Tipo di errore e suggerimenti
- **Metadata**: Informazioni video quando disponibili
- **Performance**: Tempi di processing e dimensioni file

---

**🎉 Le modifiche dovrebbero risolvere la maggior parte dei problemi 403 con YouTube!**
