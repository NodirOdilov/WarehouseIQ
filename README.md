# WarehouseIQ - Warehouse Management System

A production-grade warehouse management system featuring inventory tracking, barcode/QR scanning, stock movements, picking/packing workflows, shipping integration, multi-warehouse support, zone management, and real-time stock alerts.

## Architecture

- **Backend:** Django 5.x + Django REST Framework
- **Frontend:** React 18 with Redux Toolkit
- **Database:** PostgreSQL 16
- **Cache / Message Broker:** Redis 7
- **Task Queue:** Celery 5.x
- **Real-time:** Django Channels (WebSocket)
- **Reverse Proxy:** Nginx
- **Containerization:** Docker + Docker Compose

## Features

### Inventory Management
- Real-time stock level tracking across warehouses
- Batch and lot tracking with expiry management
- SKU management with barcode/QR code generation
- Stock movement history with full audit trail
- Low-stock and overstock alerts via WebSocket

### Warehouse Operations
- Multi-warehouse support with independent configurations
- Zone and bin location management
- Visual warehouse map with occupancy indicators
- Location-based inventory placement optimization

### Receiving
- Purchase order receiving with line-item verification
- Barcode scanning for fast receiving workflows
- Quality inspection flags and damage tracking
- Automatic stock level updates on receipt confirmation

### Picking and Packing
- Wave and batch picking support
- Optimized pick paths based on zone layout
- Packing slip generation with item verification
- Pick accuracy tracking and reporting

### Shipping
- Multi-carrier shipping integration (UPS, FedEx, USPS, DHL)
- Shipment tracking with status updates
- Shipping label and document generation
- Delivery confirmation and proof-of-delivery

### Reporting and Analytics
- Inventory valuation reports
- Stock movement analytics
- Warehouse utilization metrics
- Picking efficiency dashboards
- Customizable date-range filtering

### Security
- JWT-based authentication with token refresh
- Role-based access control (Admin, Manager, Staff, Viewer)
- Per-warehouse permission assignments
- Full audit logging of all data modifications

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Git

### Setup

1. Clone the repository:
```bash
git clone https://github.com/your-org/warehouseiq.git
cd warehouseiq
```

2. Copy and configure the environment file:
```bash
cp .env.example .env
# Edit .env with your preferred settings
```

3. Build and start all services:
```bash
docker-compose up --build -d
```

4. Run database migrations:
```bash
docker-compose exec backend python manage.py migrate
```

5. Create a superuser:
```bash
docker-compose exec backend python manage.py createsuperuser
```

6. Access the application:
- **Frontend:** http://localhost
- **Backend API:** http://localhost/api/
- **Admin Panel:** http://localhost/admin/
- **API Documentation:** http://localhost/api/docs/

## Development Setup (without Docker)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend
```bash
cd frontend
npm install
npm start
```

### Celery Worker
```bash
cd backend
celery -A config worker -l info
```

### Celery Beat (scheduled tasks)
```bash
cd backend
celery -A config beat -l info
```

## Project Structure

```
warehouseiq/
├── backend/
│   ├── apps/
│   │   ├── accounts/       # User management and authentication
│   │   ├── warehouses/     # Warehouse, zone, and bin management
│   │   ├── inventory/      # Products, stock levels, movements
│   │   ├── receiving/      # Inbound receiving workflows
│   │   ├── picking/        # Pick lists and packing operations
│   │   ├── shipping/       # Shipments and carrier integration
│   │   └── reports/        # Analytics and reporting
│   ├── config/             # Django project configuration
│   ├── utils/              # Shared utilities
│   └── manage.py
├── frontend/
│   ├── public/
│   └── src/
│       ├── api/            # API client modules
│       ├── components/     # Reusable React components
│       ├── pages/          # Route-level page components
│       ├── store/          # Redux store and slices
│       ├── hooks/          # Custom React hooks
│       └── styles/         # Global styles
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
└── .env.example
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/auth/login/` | POST | Obtain JWT token pair |
| `/api/auth/refresh/` | POST | Refresh access token |
| `/api/accounts/users/` | GET/POST | List/create users |
| `/api/warehouses/` | GET/POST | List/create warehouses |
| `/api/warehouses/{id}/zones/` | GET/POST | Manage warehouse zones |
| `/api/inventory/products/` | GET/POST | Product catalog |
| `/api/inventory/stock-levels/` | GET | Current stock levels |
| `/api/inventory/movements/` | GET/POST | Stock movements |
| `/api/inventory/scan/` | POST | Barcode/QR scan lookup |
| `/api/receiving/orders/` | GET/POST | Receiving orders |
| `/api/picking/picklists/` | GET/POST | Pick lists |
| `/api/shipping/shipments/` | GET/POST | Shipments |
| `/api/reports/inventory-summary/` | GET | Inventory report |
| `/api/reports/movement-analytics/` | GET | Movement analytics |

## Environment Variables

See `.env.example` for a complete list of configurable environment variables.

## Testing

```bash
# Backend tests
docker-compose exec backend python manage.py test

# Frontend tests
docker-compose exec frontend npm test
```

## License

This project is proprietary software. All rights reserved.
