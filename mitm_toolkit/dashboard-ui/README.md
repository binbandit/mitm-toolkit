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

## Architecture

- **Frontend**: React 18 with TypeScript
- **Build Tool**: Vite for fast development and optimized builds
- **UI Components**: shadcn/ui with Radix UI primitives
- **Styling**: Tailwind CSS with custom theme
- **State Management**: React hooks and context
- **API Communication**: Axios for REST, native WebSocket for real-time updates