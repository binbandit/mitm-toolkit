# MITM Toolkit Dashboard

Modern React-based dashboard for MITM Toolkit built with Vite, TypeScript, and shadcn/ui components.

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The development server will start on http://localhost:3000 and proxy API requests to the backend on port 8000.

## Building

```bash
# Build for production
npm run build
```

This will build the dashboard and output files to `../static` directory, which will be served by the FastAPI backend.

## Features

- **Real-time Updates**: WebSocket connection for live request monitoring
- **RPC Detection**: Visual indicators for JSON-RPC, gRPC, SOAP, and other RPC protocols
- **Request Details**: Full request/response inspection with headers and body
- **Filtering**: Filter requests by type (HTTP/RPC) and search
- **Request ID Display**: Easy copying of request IDs for replay via CLI
- **Modern UI**: Built with shadcn/ui components and Tailwind CSS

## GitHub Pages Deployment

The dashboard is automatically deployed to GitHub Pages on every push to the main branch, allowing users to access it without installing Node.js.

### How It Works

1. **Automatic Deployment**: GitHub Actions builds and deploys on every push to main
2. **Hosted Version**: Available at `https://[username].github.io/[repo-name]/`
3. **Local Connection**: Connects to your local MITM Toolkit instance at `localhost:8000`
4. **Configurable Backend**: Click the Settings button to specify a custom backend URL

### Using the Hosted Dashboard

1. Visit the GitHub Pages URL
2. Run your local MITM Toolkit: `mitm-toolkit dashboard`
3. The dashboard automatically connects to `localhost:8000`
4. If using a different port, click Settings and update the backend URL

### Manual Deployment

To deploy manually or to your own GitHub Pages:

```bash
cd mitm_toolkit/dashboard-ui
VITE_BASE_URL=/your-repo-name/ pnpm build
# Upload the dist folder to GitHub Pages
```

## Architecture

- **Frontend**: React 18 with TypeScript
- **Build Tool**: Vite for fast development and optimized builds
- **UI Components**: shadcn/ui with Radix UI primitives
- **Styling**: Tailwind CSS with custom theme
- **State Management**: React hooks and context
- **API Communication**: Fetch API for REST, native WebSocket for real-time updates