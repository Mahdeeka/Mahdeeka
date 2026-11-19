# فيديو الشرح: «كلمة وراها حكاية»

فيديو قصير (85 ثانية) يشرح الفعالية للمشاركين: مسح رمز الطاولة، الاسم والرقم، مدير الطاولة، التعارف، الجولات الخمس، الحكاية، الجسر، النقاش، الطلب والعرض، و«بطاقتي».

- المقاسات: ‎9:16 (للتلفون، واتساب وإنستغرام) و‎16:9 (للبروجكتور).
- الصورة كلها مرسومة بالكود (`film.js`): مشاهد الشاشة هي لقطات حقيقية من التطبيق ببيانات تجريبية (`assets/shots/`).
- الصوت: الراوية من ElevenLabs (نموذج `eleven_v3`، صوت Sarah، بالعربي مع تشكيل اللهجة): النص في `audio/script.txt` والتسجيل في `audio/vo/take2.mp3`.
- التوقيت: تفريغ Scribe للتسجيل (`audio/vo/take2.scribe.json`) ← `audio/lines.json` و`timing.js`؛ كل مشهد يبدأ مع جملته.
- الموسيقى: طبلة مركّبة بالكود (96 bpm)؛ المؤثرات مولّدة من قائمة `HITS` في `film.js`.

## إعادة البناء
من مجلد `kalima-hikaya` (يحتاج مهارة motion-reel وffmpeg):
```
node <skill>/scripts/render.mjs --film explainer --format 9x16 --video-only
node <skill>/scripts/render.mjs --film explainer --format 16x9 --video-only
uv run <skill>/scripts/beats.py explainer --synth --flavor tabla --mode dorian --tonic D --bpm 96 --duration 85 --seed 7
node <skill>/scripts/sfx.mjs explainer     # audio/sfx.wav
ffmpeg -i explainer/audio/vo/take2.mp3 -af "adelay=400|400,highpass=f=80,acompressor=threshold=-20dB:ratio=2.5:attack=10:release=200,apad=whole_dur=85" -ar 48000 -ac 2 explainer/audio/vo.wav
node <skill>/scripts/mix.mjs explainer     # out/explainer/final.mp4 + final_16x9.mp4
```
