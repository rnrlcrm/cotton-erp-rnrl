# UI/UX Design Guidelines for Cotton ERP

## Design Philosophy

**Goal**: Build "a system the world hasn't seen" - combining simplicity, intelligence, and delight.

### Core Principles

1. **Invisible Complexity** - Powerful features that feel simple
2. **AI-Native** - Intelligence embedded naturally, not bolted on
3. **Audit Transparency** - Every change visible and explainable
4. **Speed First** - Fast, responsive, optimized for high-volume data entry
5. **Context-Aware** - System anticipates needs based on workflow

## Design System

### Color Palette

**Primary** (Cotton/Trade):
- Primary Blue: `#2563EB` (Trust, stability)
- Secondary Green: `#10B981` (Success, growth)
- Accent Gold: `#F59E0B` (Premium, value)

**Neutrals**:
- Background: `#F9FAFB`
- Surface: `#FFFFFF`
- Border: `#E5E7EB`
- Text Primary: `#111827`
- Text Secondary: `#6B7280`

**Status Colors**:
- Success: `#10B981`
- Warning: `#F59E0B`
- Error: `#EF4444`
- Info: `#3B82F6`

### Typography

**Font Family**: 
- Primary: `Inter` (Clean, modern, readable)
- Monospace: `JetBrains Mono` (For codes, numbers)

**Scale**:
- H1: 2.5rem (40px) - Page titles
- H2: 2rem (32px) - Section headers
- H3: 1.5rem (24px) - Card headers
- Body: 1rem (16px) - Main content
- Small: 0.875rem (14px) - Labels, meta

### Spacing

8px base unit:
- xs: 4px
- sm: 8px
- md: 16px
- lg: 24px
- xl: 32px
- 2xl: 48px
- 3xl: 64px

## Component Library

### Navigation

**Top Bar**:
```
┌─────────────────────────────────────────────────────┐
│ Logo  Dashboard  Trade  Commodities  ... │  🔔 👤  │
└─────────────────────────────────────────────────────┘
```

**Sidebar** (Collapsible):
```
┌────────────┐
│ 📊 Dashboard│
│ 🎯 Trade Desk│
│ 📦 Commodities│
│ 🏢 Organizations│
│ 💰 Payments│
│ 📋 Reports│
│ ⚙️ Settings│
└────────────┘
```

### Forms

**Organization Form** (Example):

```
┌─────────────────────────────────────────────┐
│ Create Organization                          │
├─────────────────────────────────────────────┤
│                                             │
│  Basic Information                          │
│  ┌─────────────────────────────────────┐   │
│  │ Organization Name *                  │   │
│  │ [Type or paste from clipboard]       │   │
│  └─────────────────────────────────────┘   │
│      ↓ AI suggests: "Cotton Corporation"   │
│                                             │
│  ┌──────────────┐  ┌──────────────┐       │
│  │ Type *       │  │ Category *   │       │
│  │ [Corporation▾]│  │ [Trader▾]   │       │
│  └──────────────┘  └──────────────┘       │
│                                             │
│  Contact Details                            │
│  ┌─────────────────────────────────────┐   │
│  │ Email *                              │   │
│  │ contact@example.com                  │   │
│  └─────────────────────────────────────┘   │
│      ✓ Email validated                     │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ Phone *                              │   │
│  │ +91-                                 │   │
│  └─────────────────────────────────────┘   │
│      🤖 AI detected country: India         │
│                                             │
│  [Cancel]                    [Save & Continue →] │
└─────────────────────────────────────────────┘
```

**Smart Features**:
- Auto-complete from existing data
- AI suggestions based on input
- Real-time validation
- Keyboard shortcuts (Cmd+S to save)
- Paste detection (paste CSV, AI parses)

### Data Tables

**Commodity List** (Example):

```
┌─────────────────────────────────────────────────────────────┐
│ Commodities                        [+ Add] [Import] [Export]│
├─────────────────────────────────────────────────────────────┤
│ 🔍 Search... │ Filter: ▾All │ Category: ▾All │ Status: ▾Active│
├────┬──────────────────┬──────────┬───────────┬──────────────┤
│ ✓  │ Name             │ Category │ HSN Code  │ Last Updated │
├────┼──────────────────┼──────────┼───────────┼──────────────┤
│ □  │ Raw Cotton       │ Fiber    │ 5201      │ 2 hours ago  │
│ □  │ Cotton Yarn      │ Textile  │ 5205      │ 1 day ago    │
│ □  │ Cotton Waste     │ Waste    │ 5202      │ 3 days ago   │
│ ... (showing 1-50 of 234)                                    │
└─────────────────────────────────────────────────────────────┘
     [← Previous]  Page 1 of 5  [Next →]
```

**Smart Features**:
- Instant search (no button)
- Multi-select with Shift+Click
- Bulk actions on selection
- Column sorting/reordering
- Virtual scrolling for 10,000+ rows
- Export to Excel/CSV
- Right-click context menu

### Audit Timeline

**Organization History** (Example):

```
┌─────────────────────────────────────────────────────┐
│ Change History - Cotton Mills Ltd                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  🕐 Today, 10:30 AM                                 │
│  👤 Rajesh Kumar updated Bank Account              │
│  Changed: Account Number                           │
│    Old: ****1234                                   │
│    New: ****5678                                   │
│  Reason: "Bank account migration"                  │
│  [View Details]                                    │
│                                                     │
│  🕐 Yesterday, 3:15 PM                             │
│  👤 Priya Sharma added GST Registration            │
│  GSTIN: 27AABCU9603R1ZM                            │
│  State: Maharashtra                                │
│  [View Details]                                    │
│                                                     │
│  🕐 Nov 18, 2025                                   │
│  👤 System created Organization                    │
│  Name: Cotton Mills Ltd                            │
│  Type: Corporation                                 │
│  [View Details]                                    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Features**:
- Timeline view (default)
- Filter by user/event type/date
- Expand for full JSON diff
- Download audit log as PDF
- "Replay" view to see state at any point

### AI Assistance

**Embedded Intelligence**:

```
┌─────────────────────────────────────────────┐
│ Add Commodity                                │
├─────────────────────────────────────────────┤
│                                             │
│  Name: Raw Cotton                           │
│                                             │
│  🤖 AI Assistant:                           │
│  ┌───────────────────────────────────────┐ │
│  │ I've detected this is likely:          │ │
│  │ • Category: Natural Fiber               │ │
│  │ • HSN Code: 5201 (Cotton, not carded)  │ │
│  │ • Standard Parameters: Staple length,  │ │
│  │   Micronaire, Strength, Color           │ │
│  │                                         │ │
│  │ [✓ Apply suggestions] [✗ Dismiss]      │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  Category: [Natural Fiber ✓]               │
│  HSN Code: [5201 ✓]                        │
│                                             │
└─────────────────────────────────────────────┘
```

**AI Features**:
- Contextual suggestions
- Auto-fill from past data
- Anomaly detection ("This price seems unusual")
- Smart validation ("HSN code doesn't match category")
- Natural language search ("Show me all cotton trades from last month")

## Module-Specific UX

### 1. Organization Settings

**Layout**: Single-page with tabs

```
┌─────────────────────────────────────────────┐
│ Cotton Mills Ltd                             │
│ [Basic Info] [GST] [Bank] [Financial Years] │
├─────────────────────────────────────────────┤
│ BASIC INFORMATION                           │
│ Name: Cotton Mills Ltd          [Edit]     │
│ Type: Corporation                           │
│ ...                                         │
│                                             │
│ GST REGISTRATIONS                           │
│ ┌─────────────────────────────────────┐    │
│ │ GSTIN: 27AAB...  State: Maharashtra │    │
│ │ Primary ✓         Status: Active     │    │
│ └─────────────────────────────────────┘    │
│ [+ Add GST Registration]                    │
│                                             │
│ BANK ACCOUNTS                               │
│ ┌─────────────────────────────────────┐    │
│ │ HDFC Bank - ****1234                 │    │
│ │ Default ✓         Branch: Mumbai     │    │
│ └─────────────────────────────────────┘    │
│ [+ Add Bank Account]                        │
└─────────────────────────────────────────────┘
```

**UX Goals**:
- All info on one page (avoid navigation)
- Inline editing (click to edit)
- Expandable sections for details
- Quick add with modal forms

### 2. Commodity Master

**Layout**: Split view (List + Details)

```
┌──────────────┬──────────────────────────────┐
│ Commodities  │ Raw Cotton                   │
│ ------------ │                              │
│ ▶ Raw Cotton │ Category: Natural Fiber      │
│   Cotton Yarn│ HSN Code: 5201               │
│   Cotton W..│ GST Rate: 5%                 │
│              │                              │
│ [+ Add]      │ QUALITY PARAMETERS           │
│              │ ┌──────────────────────┐    │
│              │ │ Staple Length: 28-32mm│    │
│              │ │ Micronaire: 3.5-4.9   │    │
│              │ │ Strength: 26+ g/tex   │    │
│              │ └──────────────────────┘    │
│              │                              │
│              │ VARIETIES                    │
│              │ • DCH-32                     │
│              │ • Shankar-6                  │
│              │                              │
│              │ 🤖 AI Insights:              │
│              │ "Price trending up 12% YoY"  │
└──────────────┴──────────────────────────────┘
```

**UX Goals**:
- Master-detail pattern
- Nested entities (varieties, parameters)
- AI insights embedded
- Quick search/filter on left

### 3. Trade Desk (Future)

**Layout**: Command center dashboard

```
┌──────────────────────────────────────────────────┐
│ Trade Desk                      🔴 3 Active      │
├──────────────────────────────────────────────────┤
│ LIVE BARGAINS                                    │
│ ┌──────────────────────────────────────────┐    │
│ │ #TB-001 | Raw Cotton | 100 MT            │    │
│ │ Buyer: ABC Corp | 🟡 In Progress         │    │
│ │ Current: ₹55,000/qt | Target: ₹54,500    │    │
│ │ 🤖 AI: Price acceptable, suggest confirm  │    │
│ └──────────────────────────────────────────┘    │
│                                                  │
│ MARKET SIGNALS                                   │
│ 🔼 Cotton prices up 2.5% today                  │
│ 📊 Volume: High (120% of avg)                   │
│ ⚠️ Weather alert: Rain forecast in Punjab       │
│                                                  │
│ QUICK ACTIONS                                    │
│ [New Bargain] [View Trades] [Reports]           │
└──────────────────────────────────────────────────┘
```

**UX Goals**:
- Real-time updates
- AI recommendations
- Quick decision making
- Minimal clicks to execute

## Mobile Considerations

### Responsive Breakpoints
- Desktop: 1280px+
- Tablet: 768px - 1279px
- Mobile: < 768px

### Mobile-First Features
- Bottom navigation for key actions
- Swipe gestures (swipe left to delete)
- Thumb-friendly tap targets (44px min)
- Offline mode with sync
- Voice input for data entry
- Camera for document upload

## Accessibility (WCAG 2.1 AA)

- Keyboard navigation (Tab, Enter, Escape)
- Screen reader support (ARIA labels)
- Color contrast ratio 4.5:1 minimum
- Focus indicators
- Text resize up to 200%
- Alt text for images

## Performance Targets

- First Contentful Paint: < 1s
- Time to Interactive: < 3s
- Lighthouse Score: 90+
- Bundle Size: < 200KB (gzipped)
- 60fps animations
- Optimistic UI updates (instant feedback)

## Animation & Microinteractions

**Principles**:
- Fast but not jarring (200-300ms)
- Purposeful (guide attention)
- Skippable (respect prefers-reduced-motion)

**Examples**:
- Page transitions: Fade + slide (250ms)
- Button click: Scale down (100ms)
- Form validation: Shake on error (300ms)
- Loading states: Skeleton screens
- Success: Checkmark animation (400ms)
- List reorder: Smooth position change (300ms)

## Technology Recommendations

### Frontend Stack
- **Framework**: React 18+ (or Svelte for speed)
- **State**: Zustand (lightweight, fast)
- **Routing**: React Router v6
- **Forms**: React Hook Form + Zod validation
- **Tables**: TanStack Table (virtual scrolling)
- **Charts**: Apache ECharts (interactive)
- **UI Library**: Tailwind CSS + HeadlessUI
- **Icons**: Heroicons
- **Date/Time**: date-fns

### Data Fetching
- **API Client**: TanStack Query (caching, optimistic updates)
- **WebSockets**: Socket.io (real-time updates)
- **Optimistic UI**: Update immediately, rollback on error

### Build Tools
- **Bundler**: Vite (fast dev, HMR)
- **TypeScript**: Strict mode
- **Linting**: ESLint + Prettier
- **Testing**: Vitest + Testing Library

## File Structure (Frontend)

```
frontend/src/
├── app/              # App shell, routing
├── features/         # Feature-based modules
│   ├── organizations/
│   │   ├── api/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── types/
│   │   └── utils/
│   ├── commodities/
│   ├── trade-desk/
│   └── ...
├── shared/           # Shared components/utils
│   ├── components/   # UI library
│   ├── hooks/
│   ├── utils/
│   └── types/
├── lib/              # External integrations
└── assets/           # Images, fonts, etc.
```

## Summary

**Goal**: Build a frontend that feels like **magic**:
- Fast (instant feedback)
- Smart (AI suggestions)
- Transparent (audit trail visible)
- Beautiful (premium design)
- Accessible (works for everyone)

**Key Differentiators**:
1. **AI-Native**: Intelligence embedded naturally
2. **Audit Timeline**: Every change visible and explainable
3. **Speed**: Optimistic UI, virtual scrolling, instant search
4. **Context-Aware**: System anticipates needs

**Next**: When building frontend, start with **Organization Settings** module (simplest) to establish patterns, then scale to complex modules like Trade Desk.
