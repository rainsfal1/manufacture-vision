# Frontend Dashboard

Modern web UI for monitoring, configuration, and analytics in Manufacture Vision.

Built with Next.js 14, React 18, TypeScript, and Tailwind CSS.

## Overview

The Frontend Dashboard provides real-time visibility into manufacturing safety monitoring:

- **Live Alert Feed** - Real-time notifications of PPE violations, intrusions, and anomalies
- **Zone Visualization** - Real-time occupancy and activity monitoring
- **Incident Search** - Historical event search with advanced filtering
- **Evidence Playback** - Watch video clips of incidents with annotations
- **Compliance Analytics** - Trends, compliance rates, and violation analysis
- **Zone Editor** - Create and update detection zones with polygon drawing
- **System Status** - Hardware health, uptime, and performance metrics
- **Configuration** - Manage policies, users, and system settings

## Quick Start

### Prerequisites

- Node.js 20+
- npm 10+

### Installation

```bash
# Install dependencies
npm install

# Create environment file
cp .env.example .env.local

# Start development server
npm run dev
```

Dashboard runs at: http://localhost:3000

### Docker

```bash
docker build -t frontend-dashboard:latest .
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://localhost:8000 \
  frontend-dashboard:latest
```

## Configuration

### Environment Variables

Create `.env.local`:

```env
# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# WebSocket/SSE
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Authentication
NEXT_PUBLIC_AUTH_ENABLED=true
NEXT_PUBLIC_JWT_STORAGE=localStorage

# Feature Flags
NEXT_PUBLIC_FEATURES_ANALYTICS=true
NEXT_PUBLIC_FEATURES_ZONE_EDITOR=true
NEXT_PUBLIC_FEATURES_PLAYBACK=true
NEXT_PUBLIC_FEATURES_EXPORT=true

# UI Configuration
NEXT_PUBLIC_ALERT_FEED_ROWS=10
NEXT_PUBLIC_CHART_REFRESH_INTERVAL=5000
NEXT_PUBLIC_LIVE_UPDATE_INTERVAL=1000

# Analytics
NEXT_PUBLIC_ANALYTICS_ENABLED=false
NEXT_PUBLIC_ANALYTICS_ID=

# Environment
NODE_ENV=development
NEXT_PUBLIC_ENV=development
```

### API Connection

The dashboard connects to the backend API:

```env
# Development
NEXT_PUBLIC_API_URL=http://localhost:8000

# Production
NEXT_PUBLIC_API_URL=https://api.manufacture-vision.com
```

The API base URL is set at runtime, not build time, allowing deployment without rebuilds.

## Features

### Live Alert Feed

Real-time stream of safety events with SSE (Server-Sent Events).

Features:
- Auto-scrolling alert list
- Color-coded severity (red: critical, orange: high, yellow: medium)
- Event details on click
- Filter by event type
- Evidence clip link for each alert

### Zone Visualization

Real-time overlay of detection zones on live camera feed.

Features:
- Polygon zone display
- Current occupancy count
- PPE compliance status per person
- Color-coded heat map (no one/low/high occupancy)
- Click to drill into specific zone

### Incident Search

Advanced historical event search with filtering.

Features:
- Search by event type, date range, zone, severity
- Full-text search on descriptions
- Export results to CSV
- Pagination (20/50/100 per page)
- Sort by timestamp, severity, source

### Evidence Playback

Watch incident video clips with annotations.

Features:
- Full MP4 playback
- Scrubber timeline
- Frame-by-frame stepping
- Bounding box overlays
- Download clip
- Print frame

### Compliance Analytics

Dashboard with compliance metrics and trends.

Features:
- Compliance rate (%)
- Total violations by zone
- Violations by type (pie chart)
- Daily trend (line chart)
- Most common violation
- Comparison with previous period

### Zone Editor

Create and edit detection zones with polygon drawing UI.

Features:
- Draw polygons on reference image
- Save zone configuration
- Edit existing zones
- Delete zones
- Export/import zone JSON
- Validate polygon (must be >3 points, no self-intersecting)

### System Status

Monitor system health and performance.

Features:
- Backend API status
- Database connectivity
- Redis status
- MinIO storage status
- Perception node status per camera
- CPU/memory usage
- Network latency

## Development

### Project Structure

```
frontend-dashboard/
├── src/
│   ├── app/                    # Next.js app directory
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Home/login page
│   │   ├── globals.css         # Global styles
│   │   ├── dashboard/
│   │   │   └── page.tsx        # Main dashboard page
│   │   ├── login/
│   │   │   └── page.tsx        # Login page
│   │   ├── api/                # Next.js API routes
│   │   │   └── auth/
│   │   │       └── route.ts    # Token refresh endpoint
│   │   └── (auth)/             # Auth group layout
│   │       └── layout.tsx
│   ├── components/             # React components
│   │   ├── AlertCard.tsx       # Individual alert
│   │   ├── LiveAlertFeed.tsx   # Alert stream
│   │   ├── IncidentHistory.tsx # Event search
│   │   ├── SystemStatus.tsx    # Health status
│   │   ├── ZoneGrid.tsx        # Zone visualization
│   │   ├── ZoneEditorModal.tsx # Zone editor
│   │   ├── ConfigPanel.tsx     # Configuration UI
│   │   ├── AnalyticsPanel.tsx  # Metrics charts
│   │   ├── VideoModal.tsx      # Clip playback
│   │   ├── ConsoleLayout.tsx   # Dashboard layout
│   │   └── common/             # Shared components
│   │       ├── Button.tsx
│   │       ├── Card.tsx
│   │       ├── Modal.tsx
│   │       ├── Table.tsx
│   │       └── Input.tsx
│   ├── hooks/                  # Custom React hooks
│   │   ├── useAuth.ts          # Authentication
│   │   ├── useApi.ts           # API calls
│   │   ├── useEvents.ts        # Event stream
│   │   └── useForm.ts          # Form state
│   ├── lib/                    # Utilities
│   │   ├── api.ts              # API client
│   │   ├── auth.ts             # Auth utilities
│   │   ├── storage.ts          # LocalStorage wrapper
│   │   ├── formatting.ts       # Format functions
│   │   └── constants.ts        # App constants
│   ├── types/                  # TypeScript types
│   │   ├── api.ts              # API response types
│   │   ├── events.ts           # Event types
│   │   ├── auth.ts             # Auth types
│   │   └── index.ts            # Shared types
│   └── styles/                 # Styling
│       ├── globals.css         # Global styles
│       ├── components.css      # Component styles
│       └── animations.css      # Animation keyframes
├── public/                     # Static assets
│   ├── icons/
│   ├── images/
│   └── favicon.ico
├── package.json
├── tsconfig.json               # TypeScript config
├── next.config.mjs             # Next.js config
├── tailwind.config.ts          # Tailwind config
├── postcss.config.mjs          # PostCSS config
├── Dockerfile                  # Container image
└── README.md                   # This file
```

### Running Development Server

```bash
npm run dev
```

Server runs at http://localhost:3000 with hot-reload enabled.

### Building for Production

```bash
# Build
npm run build

# Start production server
npm start
```

Or with Docker:

```bash
docker build -t frontend-dashboard:latest .
docker run -p 3000:3000 frontend-dashboard:latest
```

### Code Quality

Format:

```bash
npm run format
```

Type check:

```bash
npm run type-check
```

Linting:

```bash
npm run lint
```

All three:

```bash
npm run validate
```

## Component Documentation

### AlertCard

Displays individual event/alert.

```tsx
<AlertCard
  event={{
    id: "evt-123",
    type: "ppe_violation",
    severity: "high",
    timestamp: "2024-04-29T10:25:30Z",
    description: "Worker missing helmet in assembly area"
  }}
  onClickEvidence={() => handlePlayback("evt-123")}
/>
```

### LiveAlertFeed

Real-time alert stream with SSE.

```tsx
<LiveAlertFeed
  apiUrl="http://localhost:8000"
  token="eyJ0eXAiOiJKV1QiLCJhbGc..."
  maxItems={20}
/>
```

Props:
- `apiUrl` - Backend API URL
- `token` - JWT authentication token
- `maxItems` - Max alerts to display
- `onEventClick` - Callback when alert is clicked
- `autoScroll` - Auto-scroll to new events (default: true)

### ZoneGrid

Displays detection zones with live occupancy.

```tsx
<ZoneGrid
  zones={[
    {
      id: "zone-assembly",
      name: "Assembly Area",
      polygon: [{x: 0, y: 0}, {x: 640, y: 480}]
    }
  ]}
  occupancy={{
    "zone-assembly": {count: 3, compliant: 2}
  }}
/>
```

### AnalyticsPanel

Displays compliance metrics and charts.

```tsx
<AnalyticsPanel
  startDate={new Date("2024-04-01")}
  endDate={new Date("2024-04-30")}
  zoneId="zone-assembly"
/>
```

### VideoModal

Evidence clip playback.

```tsx
<VideoModal
  isOpen={true}
  clipId="clip-789"
  onClose={() => setOpen(false)}
/>
```

## API Integration

### Authentication

```ts
import { useAuth } from '@/hooks/useAuth';

const { login, token, isAuthenticated } = useAuth();

// Login
await login('admin', 'password');

// Use token in API calls
const headers = {
  'Authorization': `Bearer ${token}`
};
```

### Event Fetching

```ts
import { useApi } from '@/hooks/useApi';

const { data: events, isLoading } = useApi(
  '/events?limit=10',
  { method: 'GET' }
);
```

### SSE Subscription

```ts
import { useEvents } from '@/hooks/useEvents';

const { events, isConnected } = useEvents(token);

// events is auto-updated with new events
```

### Form Submission

```ts
import { useForm } from '@/hooks/useForm';

const { values, handleChange, handleSubmit } = useForm({
  zone_name: '',
  ppe_required: []
}, async (values) => {
  const response = await api.post('/zones', values);
});

<form onSubmit={handleSubmit}>
  <input
    value={values.zone_name}
    onChange={handleChange}
    name="zone_name"
  />
</form>
```

## Styling

### Tailwind CSS

All components use Tailwind utility classes:

```tsx
<div className="flex flex-col gap-4 p-6 bg-white rounded-lg shadow">
  <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
  <p className="text-gray-600">Real-time safety events</p>
</div>
```

### Custom CSS

Global styles in `src/styles/globals.css`:

```css
:root {
  --color-danger: #ef4444;
  --color-warning: #f97316;
  --color-success: #22c55e;
  --color-info: #3b82f6;
}

@layer components {
  .btn-primary {
    @apply px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition;
  }
}
```

### Animations

Keyframe animations in `src/styles/animations.css`:

```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.animate-fade-in {
  animation: fadeIn 0.3s ease-in;
}
```

## State Management

### React Context

Global auth context:

```tsx
import { useAuth } from '@/hooks/useAuth';

const { user, token, logout } = useAuth();
```

### Local State

Component state:

```tsx
const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
const [isLoading, setIsLoading] = useState(false);
```

### Custom Hooks

Reusable logic:

```ts
export function useAuth() {
  const [token, setToken] = useState<string | null>(null);
  
  const login = async (username: string, password: string) => {
    const response = await fetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    const data = await response.json();
    setToken(data.access_token);
  };

  return { token, login };
}
```

## Performance Optimization

### Code Splitting

Automatic with Next.js dynamic imports:

```tsx
const AnalyticsPanel = dynamic(() => import('@/components/AnalyticsPanel'), {
  loading: () => <div>Loading...</div>
});
```

### Image Optimization

Use Next.js Image component:

```tsx
import Image from 'next/image';

<Image
  src="/images/logo.png"
  alt="Logo"
  width={200}
  height={100}
/>
```

### Memoization

Prevent unnecessary re-renders:

```tsx
const AlertCard = memo(({ event, onClickEvidence }: Props) => {
  return <div>...</div>;
});
```

### Caching

Cache API responses:

```ts
const { data: events } = useApi('/events', {
  revalidateOnFocus: false,
  dedupingInterval: 60000  // 1 minute cache
});
```

## Debugging

### Browser DevTools

F12 opens developer tools:

1. **Console** - View logs and errors
2. **Network** - Monitor API calls
3. **React DevTools** - Inspect component state
4. **Next.js DevTools** - Debug server/client code

### Debug Logging

Enable verbose logging:

```tsx
if (process.env.NODE_ENV === 'development') {
  console.log('Event:', event);
}
```

### Network Inspection

Monitor API requests:

```bash
# In browser console
localStorage.setItem('DEBUG', '*');  // Enable debug logs
```

Check SSE connection:

```bash
# In Network tab, filter for EventStream
```

## Troubleshooting

### Dashboard Won't Load

1. Check backend is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check API URL in `.env.local`:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. Check browser console for errors (F12)

4. Clear cache:
   ```bash
   rm -rf .next
   npm run build
   npm start
   ```

### Login Not Working

1. Verify backend auth endpoint:
   ```bash
   curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin"}'
   ```

2. Check credentials in `.env.local`

3. Check token is stored:
   ```bash
   # In browser console
   localStorage.getItem('token')
   ```

### Live Alerts Not Updating

1. Check SSE connection:
   ```bash
   curl -N http://localhost:8000/notifications/live \
     -H "Authorization: Bearer $TOKEN"
   ```

2. Check browser Network tab for EventStream

3. Verify backend SSE endpoint is enabled

### Charts Not Rendering

1. Check data is loading:
   ```bash
   # In browser console
   const response = await fetch('/api/reports/compliance');
   const data = await response.json();
   console.log(data);
   ```

2. Verify Recharts is installed:
   ```bash
   npm ls recharts
   ```

3. Check component is mounted:
   ```tsx
   useEffect(() => {
     console.log('AnalyticsPanel mounted');
   }, []);
   ```

## Building for Production

### Environment Setup

```env
NEXT_PUBLIC_API_URL=https://api.manufacture-vision.com
NEXT_PUBLIC_ENV=production
NODE_ENV=production
```

### Build Optimization

```bash
# Production build
npm run build

# Check bundle size
npm run analyze
```

### Docker Deployment

```bash
# Multi-stage build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package*.json ./
RUN npm ci --only=production
EXPOSE 3000
CMD ["npm", "start"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-dashboard
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend-dashboard
  template:
    metadata:
      labels:
        app: frontend-dashboard
    spec:
      containers:
      - name: frontend
        image: frontend-dashboard:latest
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_API_URL
          value: "https://api.manufacture-vision.com"
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

## Testing

### Unit Tests

```bash
# Install testing dependencies
npm install --save-dev jest @testing-library/react

# Run tests
npm test

# Watch mode
npm test -- --watch

# Coverage
npm test -- --coverage
```

### E2E Tests

```bash
# Install Playwright
npm install --save-dev @playwright/test

# Run E2E tests
npx playwright test

# Debug
npx playwright test --debug
```

## SEO & Meta Tags

Configured in `src/app/layout.tsx`:

```tsx
export const metadata: Metadata = {
  title: 'Manufacture Vision Dashboard',
  description: 'Real-time manufacturing safety monitoring',
  keywords: ['safety', 'monitoring', 'manufacturing', 'AI'],
};
```

## License

Proprietary - All rights reserved
