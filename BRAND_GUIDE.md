# SpecScribe Brand Quick Reference

**Version 1.0** | One-page guide for developers, designers, and content creators

> For complete details, see [branding.md](./branding.md)

---

## Brand Identity At-a-Glance

**Mission:** Eliminate ambiguity in software development by transforming conversations into clear, precise, actionable requirements.

**Primary Tagline:** **"Your AI Business Analyst"**

**Positioning:** For software teams, project managers, and innovators, SpecScribe is the AI-powered business analyst that transforms unstructured conversations into clear, developer-ready specifications.

---

## Visual Identity

### Color Palette

#### Primary: Deep Indigo
```
#000831  deep-indigo-500   Primary brand, backgrounds, headers
#21376E  deep-indigo-400   Buttons, CTAs
#6885AD  deep-indigo-300   Hover states, borders
#E9EFF5  deep-indigo-50    Light backgrounds
#D3E0EB  deep-indigo-100   Subtle accents
```

**Usage:** Navigation, headers, primary buttons, logo, documentation headers

#### Accent: Benzol Green
```
#00d471  benzol-green-500  Success states, completed items
#009E4A  benzol-green-700  Success buttons
#8EEDCE  benzol-green-300  Progress indicators
```

**Usage:** Completion states, "Requirements Generated" messages, progress indicators, export buttons

#### Warning/Error: Jasper Red
```
#fa2b00  jasper-red-500    Errors, warnings
#E02500  jasper-red-600    Danger buttons (delete, cancel)
#FFF9F2  jasper-red-50     Warning backgrounds
```

**Usage:** Error messages, destructive actions, validation warnings, critical alerts

#### Processing: Amber
```
#F59E0B  amber-500         In-progress indicators
#FEF3C7  amber-100         Warning/caution backgrounds
#D97706  amber-600         Processing states
```

**Usage:** "Analyzing..." loading states, "Generating..." progress, unsaved changes

---

### Logo Assets

**Location:** `/logos/` and root directory

| Asset | File | Usage |
|-------|------|-------|
| Icon (SVG) | `logo-icon.svg` | Favicons, app icons, social profiles |
| Full Logo (SVG) | `logo-full.svg` | Headers, documentation, marketing |
| Favicon | `logos/favicon.ico` | Browser tab icon |
| Apple Touch | `logos/apple-touch-icon.png` | iOS home screen |
| Social Share | `logos/og-image.png` | Open Graph preview image |
| PNG Icons | `logos/icon-{16,32,48,64,128,256,512}.png` | Various sizes |
| PNG Full | `logos/full-{200w,400w,800w}.png` | Responsive images |

**Logo Concept:** Deep indigo square (foundation/architect) + benzol green arrow (transformation/sage)

---

### Typography

#### Headings: IBM Plex Sans
```css
font-family: 'IBM Plex Sans', sans-serif;
```

**Usage:** Hero headlines, section headings, navigation, button labels, interview questions

**Weights:**
- `font-weight: 700` (Bold) - For "Spec" in logo and main headings
- `font-weight: 400` (Regular) - For "Scribe" in logo and subheadings

#### Body Text: Inter
```css
font-family: 'Inter', sans-serif;
```

**Usage:** Paragraphs, lists, form labels, descriptions, body copy

**Weights:** 400 (Regular), 500 (Medium), 600 (Semibold)

#### Monospace: JetBrains Mono
```css
font-family: 'JetBrains Mono', monospace;
```

**Usage:** Code snippets, CLI output, API docs, file paths, commands

---

## Brand Voice & Tone

### Personality: The Sage-Architect

**Traits:** Methodical, insightful, quietly confident, uncompromising on clarity, collaborative

### Voice (Consistent Across All Channels)
Confident, intelligent, helpful, and precise

### Tone (Context-Dependent)

| Context | Tone | Example |
|---------|------|---------|
| **UI/CLI** | Direct, instructional | "What problem are you trying to solve?" |
| **Marketing** | Aspirational, benefit-focused | "Turn conversations into code-ready specs" |
| **Documentation** | Technical, precise, exhaustive | "Supports Claude, GPT, and Gemini providers" |
| **Errors** | Helpful, action-oriented | "This answer needs more detail. Can you describe specific workflows?" |

---

## Key Messaging

### Message Hierarchy

1. **PRIMARY:** "Your AI Business Analyst"
   → Unique positioning as intelligent team member, not just a tool

2. **SECONDARY:** "From Vague Idea to Code-Ready Spec"
   → Emphasizes transformation and quality of output

3. **TERTIARY:** "Adapts to Your Workflow"
   → Highlights flexibility (Web/CLI/API, multiple AI providers)

### Secondary Taglines (Context-Specific)

- **Developer-focused:** "Turn Conversations Into Code-Ready Specs"
- **Process-focused:** "From Conversation to Specification"
- **Aspirational:** "Build on a Better Blueprint"
- **Emotional:** "The Missing Member of Your Dev Team"

### Persona-Specific Benefits

**For Project Managers (Priya):**
- "Stop chasing stakeholders for missing details"
- "Generate professional specs in minutes, not hours"
- "One source of truth for your entire team"

**For Developers (David):**
- "No more vague tickets or missing requirements"
- "Integrates with your terminal workflow"
- "Know what to build and why before writing a line of code"

**For Founders (Sam):**
- "Turn your idea into a technical blueprint"
- "Hire developers with confidence"
- "Understand what's essential vs. nice-to-have"

---

## UI Component Guidelines

### Buttons

**Primary CTA:**
```html
bg-deep-indigo-400 hover:bg-deep-indigo-300 text-white
```

**Success/Completion:**
```html
bg-benzol-green-700 hover:bg-benzol-green-500 text-white
```

**Danger/Destructive:**
```html
bg-jasper-red-600 hover:bg-jasper-red-500 text-white
```

**Secondary/Ghost:**
```html
border-deep-indigo-300 text-deep-indigo-500 hover:bg-deep-indigo-50
```

### States & Feedback

**Success Messages:**
```html
bg-benzol-green-50 border-benzol-green-500 text-benzol-green-700
```

**Error Messages:**
```html
bg-jasper-red-50 border-jasper-red-500 text-jasper-red-600
```

**Warning/Incomplete:**
```html
bg-amber-100 border-amber-500 text-amber-600
```

**Processing/Loading:**
```html
bg-amber-50 text-amber-600
```

### Progress Indicators

- **Completed:** `text-benzol-green-500` or `bg-benzol-green-500`
- **In Progress:** `text-amber-500` or `bg-amber-500`
- **Pending:** `text-deep-indigo-200` or `bg-deep-indigo-100`

---

## Design Principles

1. **Generous Whitespace** - Let content breathe, don't crowd
2. **Clear Hierarchy** - Use size, weight, and color to guide attention
3. **Consistent Iconography** - Simple, geometric icons matching IBM Plex Sans
4. **Purposeful Color** - Use accents (green, red, amber) sparingly and meaningfully
5. **Progressive Disclosure** - Show information when needed, not all at once

---

## Quick Dos and Don'ts

### ✅ Do

- **Use "SpecScribe"** consistently
- **Emphasize methodology** over raw AI capability ("guided interview", "8 question categories")
- **Position as team member** ("Your AI Business Analyst", "Missing member of your dev team")
- **Show transformation** (conversation → specification)
- **Be specific** about benefits (time saved, completeness, prioritization)

### ❌ Don't

- **Use generic AI language** ("AI-powered tool", "smart assistant")
- **Oversell or use superlatives** (let results speak for themselves)
- **Compare to unrelated tools** (focus on BA positioning)
- **Use emojis** unless explicitly requested by user

---

## Content Templates

### Hero Headline Pattern
```
[Action Verb] + [Benefit] + [Without Pain Point]

Examples:
- "Turn Conversations Into Code-Ready Specs"
- "Build Better Software Without the Guesswork"
- "Gather Complete Requirements Without Endless Meetings"
```

### Feature Description Pattern
```
[What It Does] + [Why It Matters] + [Result]

Example:
"Adaptive interview engine asks intelligent follow-up questions based on
your answers, ensuring every critical detail is captured so developers
have complete context from day one."
```

### CTA Button Text
```
Primary: "Start Your Interview" | "Create Specification"
Secondary: "See How It Works" | "View Demo"
Download: "Export Requirements" | "Download Spec"
```

---

## Example Copy Snippets

### Marketing Copy
> "Most teams can't afford a full-time business analyst. SpecScribe gives you the structured methodology and intelligent questioning of an experienced BA—available instantly, adapting to your workflow."

### Technical Copy
> "SpecScribe uses an 8-category question framework to systematically gather project scope, user needs, technical constraints, and success metrics. Powered by Claude, GPT, or Gemini, it analyzes your answers to ask relevant follow-ups and assess completeness."

### Error/Validation Copy
> "This answer could use more detail. Try describing specific user workflows or scenarios to help us capture complete requirements."

---

## Competitive Differentiation

| Dimension | SpecScribe's Advantage |
|-----------|----------------------|
| **Methodology** | Guided 8-category interview vs. blank page or generic chat |
| **Intelligence** | Adaptive follow-ups and answer quality analysis |
| **Output** | Prioritized requirements (MUST/SHOULD/COULD) with rationale |
| **Flexibility** | Web UI, CLI, and API—fits any workflow |
| **AI Choice** | Claude, GPT, or Gemini—not locked into one provider |

---

## Quick Brand Checklist

Before publishing any content, ask:

- [ ] Does it use "SpecScribe" (not "Requirements Bot")?
- [ ] Does it emphasize methodology over AI magic?
- [ ] Is the tone confident but not boastful?
- [ ] Does it solve a specific user pain point?
- [ ] Is the benefit clear and measurable?
- [ ] Does it align with the "Sage-Architect" personality?

---

**For Full Details:** See [branding.md](./branding.md) (comprehensive 1000-line strategy document)

**Questions?** Contact the brand steward or open an issue in the repo.
