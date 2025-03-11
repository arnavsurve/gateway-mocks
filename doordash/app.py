import asyncio
import json
import random
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import AsyncIterator, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

# Create MCP server
mcp = FastMCP("DoorDash")

# Global app state reference
_app_state = None


# Data models
@dataclass
class DeliveryStatus:
    CREATED = "CREATED"
    CONFIRMED = "CONFIRMED"
    DASHER_ASSIGNED = "DASHER_ASSIGNED"
    PICKUP_IN_PROGRESS = "PICKUP_IN_PROGRESS"
    ENROUTE_TO_DROPOFF = "ENROUTE_TO_DROPOFF"
    DELIVERED = "DELIVERED"
    CANCELED = "CANCELED"


@dataclass
class Dasher:
    id: str
    name: str
    rating: float
    vehicle_type: str
    phone_number: str


@dataclass
class Location:
    address: str
    business_name: Optional[str] = None
    phone_number: Optional[str] = None
    instructions: Optional[str] = None


@dataclass
class Delivery:
    external_delivery_id: str
    pickup: Location
    dropoff: Location
    order_value: int  # in cents
    status: str = DeliveryStatus.CREATED
    created_at: datetime = field(default_factory=datetime.now)
    estimated_delivery_time: Optional[datetime] = None
    dasher: Optional[Dasher] = None
    tracking_url: Optional[str] = None

    def to_dict(self):
        result = {
            "external_delivery_id": self.external_delivery_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "pickup": {
                "address": self.pickup.address,
                "business_name": self.pickup.business_name,
                "phone_number": self.pickup.phone_number,
                "instructions": self.pickup.instructions,
            },
            "dropoff": {
                "address": self.dropoff.address,
                "business_name": self.dropoff.business_name,
                "phone_number": self.dropoff.phone_number,
                "instructions": self.dropoff.instructions,
            },
            "order_value": self.order_value,
        }

        if self.estimated_delivery_time:
            result["estimated_delivery_time"] = self.estimated_delivery_time.isoformat()

        if self.dasher:
            result["dasher"] = {
                "id": self.dasher.id,
                "name": self.dasher.name,
                "rating": self.dasher.rating,
                "vehicle_type": self.dasher.vehicle_type,
                "phone_number": self.dasher.phone_number,
            }

        if self.tracking_url:
            result["tracking_url"] = self.tracking_url

        return result


# Application state
@dataclass
class AppState:
    deliveries: Dict[str, Delivery] = field(default_factory=dict)
    dashers: List[Dasher] = field(default_factory=list)

    def generate_sample_dashers(self):
        """Generate a list of sample dashers"""
        self.dashers = [
            Dasher(
                id="D1001",
                name="Alex Johnson",
                rating=4.8,
                vehicle_type="car",
                phone_number="+16505551234",
            ),
            Dasher(
                id="D1002",
                name="Maya Rodriguez",
                rating=4.9,
                vehicle_type="bicycle",
                phone_number="+16505552345",
            ),
            Dasher(
                id="D1003",
                name="Jamal Williams",
                rating=4.7,
                vehicle_type="car",
                phone_number="+16505553456",
            ),
            Dasher(
                id="D1004",
                name="Sarah Chen",
                rating=4.95,
                vehicle_type="scooter",
                phone_number="+16505554567",
            ),
            Dasher(
                id="D1005",
                name="Carlos Mendez",
                rating=4.8,
                vehicle_type="car",
                phone_number="+16505555678",
            ),
        ]

    def get_random_dasher(self) -> Dasher:
        """Get a random dasher from the list"""
        if not self.dashers:
            self.generate_sample_dashers()
        return random.choice(self.dashers)


# Server lifespan management
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppState]:
    """Initialize and clean up server resources"""
    global _app_state

    # Initialize application state
    app_state = AppState()
    app_state.generate_sample_dashers()
    _app_state = app_state

    # Set up background tasks
    tasks = []

    try:
        yield app_state
    finally:
        # Clean up background tasks
        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)


# Initialize server with lifespan
mcp = FastMCP("DoorDash", lifespan=app_lifespan)


# Helper functions
def generate_delivery_id() -> str:
    """Generate a unique delivery ID"""
    return f"D-{str(uuid.uuid4())[:8]}"


def generate_tracking_url(delivery_id: str) -> str:
    """Generate a fake tracking URL"""
    return f"https://doordash.com/tracking/{delivery_id}"


async def simulate_delivery_progress(delivery_id: str, ctx: Context):
    """Simulate the progress of a delivery through various stages"""
    app_state = ctx.request_context.lifespan_context
    delivery = app_state.deliveries.get(delivery_id)

    if not delivery:
        return

    # Update to confirmed
    await asyncio.sleep(2)
    delivery.status = DeliveryStatus.CONFIRMED
    await ctx.info(f"Delivery {delivery_id} confirmed")

    # Assign dasher
    await asyncio.sleep(5)
    delivery.dasher = app_state.get_random_dasher()
    delivery.status = DeliveryStatus.DASHER_ASSIGNED
    delivery.tracking_url = generate_tracking_url(delivery_id)
    delivery.estimated_delivery_time = datetime.now() + timedelta(
        minutes=random.randint(25, 45)
    )
    await ctx.info(f"Dasher {delivery.dasher.name} assigned to delivery {delivery_id}")

    # Pickup in progress
    await asyncio.sleep(8)
    delivery.status = DeliveryStatus.PICKUP_IN_PROGRESS
    await ctx.info(f"Dasher {delivery.dasher.name} arriving at pickup location")

    # Enroute to dropoff
    await asyncio.sleep(5)
    delivery.status = DeliveryStatus.ENROUTE_TO_DROPOFF
    await ctx.info(f"Dasher {delivery.dasher.name} en route to delivery address")

    # Delivered
    await asyncio.sleep(10)
    delivery.status = DeliveryStatus.DELIVERED
    await ctx.info(f"Delivery {delivery_id} completed")


# MCP Tools
@mcp.tool()
async def create_delivery(
    external_delivery_id: Optional[str],
    pickup_address: str,
    pickup_business_name: Optional[str] = None,
    pickup_phone_number: Optional[str] = None,
    pickup_instructions: Optional[str] = None,
    dropoff_address: str = None,
    dropoff_business_name: Optional[str] = None,
    dropoff_phone_number: Optional[str] = None,
    dropoff_instructions: Optional[str] = None,
    order_value: int = 1999,  # in cents
    ctx: Context = None,
) -> str:
    """
    Create a new delivery request.

    Args:
        external_delivery_id: Optional unique ID for the delivery
        pickup_address: Address where items will be picked up
        pickup_business_name: Name of the business for pickup
        pickup_phone_number: Contact phone for pickup location
        pickup_instructions: Special instructions for pickup
        dropoff_address: Address where items will be delivered
        dropoff_business_name: Name of the business for dropoff
        dropoff_phone_number: Contact phone for dropoff location
        dropoff_instructions: Special instructions for dropoff
        order_value: Order value in cents (default: $19.99)

    Returns:
        Delivery details as JSON
    """
    app_state = ctx.request_context.lifespan_context

    # Generate delivery ID if not provided
    if not external_delivery_id:
        external_delivery_id = generate_delivery_id()

    # Create locations
    pickup = Location(
        address=pickup_address,
        business_name=pickup_business_name,
        phone_number=pickup_phone_number,
        instructions=pickup_instructions,
    )

    dropoff = Location(
        address=dropoff_address,
        business_name=dropoff_business_name,
        phone_number=dropoff_phone_number,
        instructions=dropoff_instructions,
    )

    # Create delivery
    delivery = Delivery(
        external_delivery_id=external_delivery_id,
        pickup=pickup,
        dropoff=dropoff,
        order_value=order_value,
    )

    # Store delivery
    app_state.deliveries[external_delivery_id] = delivery

    # Start background simulation
    asyncio.create_task(simulate_delivery_progress(external_delivery_id, ctx))

    return json.dumps(delivery.to_dict(), indent=2)


@mcp.tool()
async def get_delivery_status(delivery_id: str, ctx: Context = None) -> str:
    """
    Get the current status of a delivery.

    Args:
        delivery_id: ID of the delivery to check

    Returns:
        Current delivery status and details
    """
    app_state = ctx.request_context.lifespan_context
    delivery = app_state.deliveries.get(delivery_id)

    if not delivery:
        return json.dumps({"error": "Delivery not found", "delivery_id": delivery_id})

    return json.dumps(delivery.to_dict(), indent=2)


@mcp.tool()
async def cancel_delivery(delivery_id: str, ctx: Context = None) -> str:
    """
    Cancel a delivery that is not yet picked up.

    Args:
        delivery_id: ID of the delivery to cancel

    Returns:
        Confirmation of cancellation
    """
    app_state = ctx.request_context.lifespan_context
    delivery = app_state.deliveries.get(delivery_id)

    if not delivery:
        return json.dumps({"error": "Delivery not found", "delivery_id": delivery_id})

    non_cancellable_statuses = [
        DeliveryStatus.DELIVERED,
        DeliveryStatus.CANCELED,
        DeliveryStatus.ENROUTE_TO_DROPOFF,
    ]

    if delivery.status in non_cancellable_statuses:
        return json.dumps(
            {
                "error": "Cannot cancel delivery",
                "status": delivery.status,
                "reason": "Delivery is already in progress, completed, or canceled",
            }
        )

    delivery.status = DeliveryStatus.CANCELED

    return json.dumps(
        {
            "success": True,
            "message": "Delivery canceled successfully",
            "delivery": delivery.to_dict(),
        },
        indent=2,
    )


@mcp.tool()
async def list_active_deliveries(ctx: Context = None) -> str:
    """
    List all active deliveries.

    Returns:
        List of all active deliveries
    """
    app_state = ctx.request_context.lifespan_context
    active_deliveries = {
        delivery_id: delivery.to_dict()
        for delivery_id, delivery in app_state.deliveries.items()
        if delivery.status != DeliveryStatus.DELIVERED
        and delivery.status != DeliveryStatus.CANCELED
    }

    return json.dumps(
        {"count": len(active_deliveries), "deliveries": active_deliveries}, indent=2
    )


@mcp.resource("delivery://{delivery_id}")
async def delivery_resource(delivery_id: str) -> str:
    """
    Get details for a specific delivery.
    """
    global _app_state
    delivery = _app_state.deliveries.get(delivery_id)

    if not delivery:
        return json.dumps({"error": "Delivery not found", "delivery_id": delivery_id})

    return json.dumps(delivery.to_dict(), indent=2)


@mcp.resource("deliveries://active")
async def active_deliveries_resource() -> str:
    """
    Get a list of all active deliveries.
    """
    global _app_state
    active_deliveries = {
        delivery_id: delivery.to_dict()
        for delivery_id, delivery in _app_state.deliveries.items()
        if delivery.status != DeliveryStatus.DELIVERED
        and delivery.status != DeliveryStatus.CANCELED
    }

    return json.dumps(
        {"count": len(active_deliveries), "deliveries": active_deliveries}, indent=2
    )


@mcp.resource("dashers://list")
async def dashers_resource() -> str:
    """
    Get a list of available dashers.
    """
    global _app_state
    dashers_data = [
        {
            "id": dasher.id,
            "name": dasher.name,
            "rating": dasher.rating,
            "vehicle_type": dasher.vehicle_type,
        }
        for dasher in _app_state.dashers
    ]

    return json.dumps({"count": len(dashers_data), "dashers": dashers_data}, indent=2)


@mcp.prompt()
def create_delivery_prompt() -> str:
    """
    Create a prompt for helping users create a new delivery.
    """
    return """
    I'll help you create a new delivery. Please provide the following information:
    
    1. Pickup address (required)
    2. Dropoff address (required)
    3. Any special instructions for pickup or dropoff
    4. Business names for the pickup and dropoff locations (if applicable)
    5. Contact phone numbers (if applicable)
    
    I'll then use this information to create a delivery for you.
    """


@mcp.prompt()
def track_delivery_prompt(delivery_id: str) -> str:
    """
    Create a prompt for tracking a specific delivery.
    """
    return f"""
    I'll help you track delivery {delivery_id}. Here's what I know about this delivery:
    
    I'll look up the current status of this delivery and provide you with all the details including:
    - Current status
    - Estimated delivery time (if available)
    - Dasher information (if assigned)
    - Pickup and dropoff details
    
    Is there anything specific about this delivery that you want to know?
    """


# Run the server when executed directly
if __name__ == "__main__":
    mcp.run()
