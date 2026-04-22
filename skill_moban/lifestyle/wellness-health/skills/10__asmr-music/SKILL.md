---
name: asmr-music
description: "Provide professional ASMR music recommendations and playback services to help users achieve sleep aid, heart rate regulation, and focus enhancement through scientifically designed audio. Use when user wants to (1) relax, sleep, or fall asleep, (2) regulate heart rate or relieve anxiety, (3) improve focus and concentration for study or work, (4) find background white noise or ambient sounds, (5) practice meditation or deep breathing, (6) set up automatic daily reminders for ASMR listening. Keywords: sleep, relax, meditation, heart rate, anxiety, focus, concentration, white noise, ASMR, background music, calming, stress relief, daily reminder, nightly routine."
---

# ASMR Music Assistant

Provide professional ASMR music recommendations and playback services to help users achieve physical and mental regulation through scientifically designed audio.

## Music Library

### 1. Sleep Aid Music
**Name**: Magic Drop ASMR
**Function**: Deep relaxation, sleep induction
**Best for**:
- Pre-sleep preparation
- Insomnia relief
- Nighttime meditation
- Stress release

**Playback URL**:
```
https://ohoeeluhrvswvqoinjyf.supabase.co/storage/v1/object/sign/music/asmr_magic_drop.mp3?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV9hYzljYmQ1NS03MDkyLTRhNzAtYmYwYS1iN2U3YzllNWZjMzMiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJtdXNpYy9hc21yX21hZ2ljX2Ryb3AubXAzIiwiaWF0IjoxNzczOTA3NjMyLCJleHAiOjE4MDU0NDM2MzJ9.33r_Dwo2t_7P2PlZzRRyDEAnBYtQpeziJvfsf8d8sjo
```

### 2. Heart Rate Regulation & Focus Enhancement
**Name**: Concentrate Flow
**Function**: Heart rate regulation, focus improvement
**Best for**:
- Study and work sessions
- Deep concentration
- Heart rate regulation
- Anxiety relief
- Creative thinking

**Playback URL**:
```
https://ohoeeluhrvswvqoinjyf.supabase.co/storage/v1/object/sign/music/concentrate.mp3?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV9hYzljYmQ1NS03MDkyLTRhNzAtYmYwYS1iN2U3YzllNWZjMzMiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJtdXNpYy9jb25jZW50cmF0ZS5tcDMiLCJpYXQiOjE3NzM5MDc2NjQsImV4cCI6MTgwNTQ0MzY2NH0.N0bTqLnmF5IMbn980WdIvOljQiGCjEoDaLJ2M6Mb2d8
```

## Daily Reminder Feature

This skill supports automatic daily reminders at 22:00 (10 PM) to help you establish a healthy sleep routine.

### How It Works
- **Trigger Time**: Every day at 22:00
- **Reminder Content**: Personalized ASMR music recommendation based on your needs
- **Delivery**: Notification with direct playback link

### Enabling/Disabling Reminders

The daily reminder is configured via `cron/jobs.json`. To enable:
1. Ensure the `asmr-daily-reminder` job is present in `cron/jobs.json`
2. Set `"enabled": true`

To disable:
- Set `"enabled": false` in the job configuration, or
- Use command: `openclaw cron disable asmr-daily-reminder`

### Manual Trigger
To test the reminder immediately:
```bash
openclaw cron run asmr-daily-reminder
```

## Smart Recommendation Logic

Automatically recommend appropriate music based on user requests and context:

| Time/Context | Recommended Music | Reasoning |
|-------------|------------------|-----------|
| 22:00-06:00 | Sleep Aid Music | Night mode, help fall asleep |
| Study/Work | Focus Music | Enhance efficiency, reduce distractions |
| Anxious/Stressed | Focus Music | Heart rate regulation, calm emotions |
| Meditation/Relaxation | Sleep Aid Music | Deep relaxation, release stress |
| Nap/Power Rest | Sleep Aid Music | Short rest, quick recovery |

## Usage Patterns

### Direct Music Request
- "Help me find sleep music"
- "I want to listen to ASMR"
- "Need focus music"
- "Play something relaxing"

### Context-Based Recommendation
- "I can't sleep" → Recommend sleep aid music
- "I need to study" → Recommend focus music
- "Feeling anxious" → Recommend heart rate regulation music
- "Help me relax" → Recommend based on time of day

### Daily Reminder Requests
- "Set up daily ASMR reminders"
- "Remind me to listen to ASMR every night"
- "Enable sleep music notifications"
- "Configure nightly reminders"

### Output Format

When recommending to users, provide:
1. **Music name and description**
2. **Applicable scenarios**
3. **Playback link** (clickable)
4. **Usage suggestions** (volume, duration, etc.)

Example response:
```
Recommended for you: Magic Drop ASMR

Function: Deep relaxation and sleep aid
Suggested duration: 15-30 minutes
Suggested volume: 20-40%

[Click to Play](music-url)

Usage tip: Play in a quiet environment with deep breathing for best results.
```

## Scientific Principles

### How ASMR Music Works
- **Low-frequency sound waves**: Activate parasympathetic nervous system, promote relaxation
- **Rhythm design**: ~60 BPM close to resting heart rate, guide heart rate synchronization
- **White noise**: Mask environmental distractions, provide stable auditory background
- **Binaural beats**: May influence brainwave frequencies, assist entering focused or relaxed states

### Usage Guidelines
1. **Sleep aid**: Start playing 15 minutes before bedtime, volume at barely audible level
2. **Focus**: Combine with Pomodoro technique (25min focus + 5min break)
3. **Heart rate regulation**: Combine with deep breathing (inhale 4s - hold 4s - exhale 6s)
4. **Environment**: Use headphones for best experience, maintain distance when using speakers

## Important Notes
- Do not play sleep aid music while driving or operating machinery
- Keep volume below 50% to protect hearing
- Discontinue use immediately if discomfort occurs
- Music is an auxiliary tool; consult professionals for serious sleep or anxiety issues
