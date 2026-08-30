# Tap Tap Stars ⭐

A no-lose tapping game for ages 0–4, rebuilt from `baby_game.py` as a touch-first
app that runs on **iPads, Android tablets, phones, and computers** — and is ready
to be wrapped for the App Store.

Every tap, key press, and finger mash is a "good" input. Nothing a child can touch
will ever exit the game, change a setting, or show an error. Grown-up stuff lives
behind a press-and-hold parent gate.

---

## The games

| Game | What happens |
|---|---|
| 🪄 **Free Play** | Any tap or key pops a glossy ball. Taps speak the colour, keys speak the letter. |
| 🎨 **Colour Splash** | Big paint splashes that say their colour name. |
| 🔤 **Letter Hunt** | A giant ghost letter is shown and spoken; tap the matching bubble. Wrong taps just gently repeat it — you can never lose. |
| 🔢 **Counting** | Tap together to ten, then a confetti fanfare and start again. |
| 🦁 **Animal Friends** | Taps pop up animals that say their name and sound ("Dog! Woof woof!"). |
| 👨‍👩‍👧 **Family Faces** | Photos you add pop up and their name is spoken. Photos never leave the device. |

Multi-touch works everywhere — two little hands at once is fine.

## The parent area (gated)

Press and **hold the ⚙ button for ~2.5 seconds**, then answer a quick sum.
Inside you can:

- Switch games or show/hide the kid menu
- **Lock to the current game** (hides the home button entirely)
- Toggle sounds and the talking voice, set volume and voice speed
- Choose uppercase **ABC** or lowercase **abc** letters
- Control how busy the screen can get
- Add / rename / remove **Family Faces** photos (stored locally in the browser, never uploaded)

Settings persist between sessions.

## Quick start

It's a static site — no build step, no dependencies.

**Just try it:** double-click `index.html`.

**Use it properly (recommended):** serve the folder over HTTP so the offline
cache and "Add to Home Screen" work:

```bash
cd baby-play
python3 -m http.server 8000
# open http://<your-computer's-ip>:8000 on the tablet (same Wi-Fi)
```

Or drop the folder on any static host (Netlify, GitHub Pages, Cloudflare Pages).

## Setting up an iPad

1. Open the URL in Safari → Share → **Add to Home Screen**. It launches
   full-screen with the app icon, and after the first load it **works offline**.
2. Turn on **Guided Access**: Settings → Accessibility → Guided Access → on.
   Open the app, triple-click the side/home button, tap Start. Now the home
   gesture, control centre, and notifications are all disabled — true toddler mode.
3. The app itself keeps the screen awake, blocks pinch-zoom/scrolling/long-press
   menus, and never navigates anywhere a child can reach.

On Android: Chrome → menu → **Add to Home screen**, and use **Settings →
Security → App pinning** for the same lockdown.

> **First sound on iPad:** Safari only allows audio/speech after a touch, so the
> voice starts with the first tap. That's a platform rule, not a bug.

## Shipping it to the App Store

The web app is deliberately structured so it can be wrapped with
[Capacitor](https://capacitorjs.com) into a real iOS/Android app:

```bash
npm create @capacitor/app@latest tap-tap-stars -- --name "Tap Tap Stars" --id com.yourname.taptapstars
cd tap-tap-stars
# copy index.html, sw.js, manifest.webmanifest and icons/ into the www/ folder
npm i @capacitor/ios @capacitor/android
npx cap add ios && npx cap sync
npx cap open ios        # opens Xcode — set your team, then Archive → Distribute
```

Things Apple will care about for the **Kids category** (already handled in-app):

- ✅ Parent gate in front of all settings/links (press-hold + arithmetic — the standard pattern)
- ✅ No ads, no tracking, no analytics, no network calls, no data collection
- ✅ Photos and settings stored only on-device
- You'll still need: an Apple Developer account ($99/yr), a privacy policy URL
  (one line: "no data is collected"), screenshots, and an age rating questionnaire.

A `pygame` script can't make this trip — that's why the game was rebuilt on web
tech. All the original behaviour (colour/letter speech, the no-lose letter game,
family faces with spoken names, generated sound effects) carried over.

## What got more robust vs. the Python version

- **Touch-first**: multi-touch pointers, no keyboard required (keyboard still works as a toy on desktop)
- **Child-safe by construction**: no Esc-to-quit, no reachable navigation; gestures, zoom, text-selection and context menus are suppressed; screen wake lock
- **Parent gate + settings panel** replacing hidden hotkeys
- **Letter Hunt redesigned for pre-readers**: tap bubbles instead of needing a keyboard
- **Faces management UI** (add/rename/delete, auto-downscaled, IndexedDB) instead of dropping files into a folder
- Speech via the built-in system voice (no `pyttsx3` install), sounds synthesized with Web Audio (no asset files)
- Handles rotation, any screen size, retina displays, old-Safari fallbacks, blocked storage, and missing speech support without crashing
- Installable PWA with offline cache

## Files

```
baby-play/
├── index.html              the whole app (HTML + CSS + JS)
├── manifest.webmanifest    PWA install metadata
├── sw.js                   offline cache (bump VERSION when you edit files)
└── icons/                  app icons (regular, maskable, apple-touch)
```
