from livekit.agents import llm
import enum
from typing import Annotated, Optional
import logging
from db_driver import DatabaseDriver, SessionManager
from guardrails import Guardrails, GuardrailStatus
from nhtsa_api import NHTSAApi

logger = logging.getLogger("user-data")
logger.setLevel(logging.INFO)

DB = DatabaseDriver()


class CarDetails(enum.Enum):
    VIN = "vin"
    Make = "make"
    Model = "model"
    Year = "year"
    Mileage = "mileage"
    Owner = "owner"


class AssistantFnc:
    def __init__(self):
        self._car_details = {
            CarDetails.VIN: "",
            CarDetails.Make: "",
            CarDetails.Model: "",
            CarDetails.Year: "",
            CarDetails.Mileage: 0,
            CarDetails.Owner: ""
        }
        self._session_id: Optional[str] = None
        self._session_manager = SessionManager()
        self._guardrails = Guardrails()
        # Cache for pending vehicle info from NHTSA decode
        self._pending_vehicle = None
    
    def set_session(self, user_identifier: str, identifier_type: str = "web"):
        """Initialize or resume a session for the user"""
        self._session_id = self._session_manager.create_session(user_identifier, identifier_type)
        
        # Load existing vehicle if session has one
        session = self._session_manager.get_session(self._session_id)
        if session and session.get("vehicle_vin"):
            car = DB.get_car_by_vin(session["vehicle_vin"])
            if car:
                self._car_details = {
                    CarDetails.VIN: car.vin,
                    CarDetails.Make: car.make,
                    CarDetails.Model: car.model,
                    CarDetails.Year: car.year,
                    CarDetails.Mileage: car.mileage,
                    CarDetails.Owner: car.owner_name
                }
        return self._session_id
    
    def log_message(self, role: str, content: str, metadata: dict = None):
        """Log a message to conversation history"""
        if self._session_id:
            self._session_manager.add_message(self._session_id, role, content, metadata)
    
    def get_conversation_history(self, limit: int = 10) -> list:
        """Get recent conversation history"""
        if self._session_id:
            return self._session_manager.get_conversation_history(self._session_id, limit)
        return []
    
    def check_input(self, user_input: str):
        """Check user input against guardrails"""
        return self._guardrails.check_input(user_input)
    
    def filter_output(self, response: str) -> str:
        """Filter AI response through guardrails"""
        return self._guardrails.filter_output(response)
    
    def get_car_str(self):
        car_str = ""
        for key, value in self._car_details.items():
            if value:
                car_str += f"{key.value}: {value}\n"
        return car_str
    
    @llm.function_tool(description="lookup a car by its vin")
    async def lookup_car(self, vin: Annotated[str, "The vin of the car to lookup"]):
        logger.info("lookup car - vin: %s", vin)
        
        # Clean VIN
        vin = vin.upper().replace(" ", "").replace("-", "")
        
        # First check local database
        result = DB.get_car_by_vin(vin)
        
        if result:
            self._car_details = {
                CarDetails.VIN: result.vin,
                CarDetails.Make: result.make,
                CarDetails.Model: result.model,
                CarDetails.Year: result.year,
                CarDetails.Mileage: result.mileage,
                CarDetails.Owner: result.owner_name
            }
            
            # Clear any pending vehicle
            self._pending_vehicle = None
            
            # Link to session
            if self._session_id:
                self._session_manager.link_vehicle_to_session(self._session_id, vin)
            
            logger.info("Successfully looked up car: %s", result)
            return f"Found your {result.year} {result.make} {result.model}. Registered to {result.owner_name}. Current mileage: {result.mileage} miles."
        
        # If not in database, try NHTSA to decode VIN
        vehicle_info = await NHTSAApi.decode_vin(vin)
        
        if vehicle_info:
            # Cache the decoded info for later use in create_car
            self._pending_vehicle = {
                "vin": vin,
                "make": vehicle_info.make,
                "model": vehicle_info.model,
                "year": vehicle_info.year
            }
            logger.info("VIN decoded via NHTSA: %s %s %s (cached for profile creation)", vehicle_info.year, vehicle_info.make, vehicle_info.model)
            return f"I found a {vehicle_info.year} {vehicle_info.make} {vehicle_info.model} but it's not in our system yet. Would you like me to create a profile for this vehicle? I'll need your name and current mileage."
        
        logger.info("Car not found for VIN: %s", vin)
        return "I couldn't find that VIN. Please double-check the number. It should be 17 characters."
    
    @llm.function_tool(description="Check for safety recalls on a vehicle using NHTSA data")
    async def check_recalls(
        self, 
        vin: Annotated[str, "The VIN of the vehicle to check for recalls. If not provided, uses the current vehicle."] = None
    ):
        """Check NHTSA recalls for a vehicle"""
        target_vin = vin or self._car_details.get(CarDetails.VIN)
        
        if not target_vin:
            return "I need a VIN to check for recalls. Could you provide your vehicle's VIN number?"
        
        # Clean VIN
        target_vin = target_vin.upper().replace(" ", "").replace("-", "")
        logger.info("Checking recalls for VIN: %s", target_vin)
        
        vehicle_info, recalls = await NHTSAApi.get_recalls_by_vin(target_vin)
        
        if not vehicle_info:
            return "I couldn't decode that VIN. Please verify it's correct."
        
        response = f"For your {vehicle_info.year} {vehicle_info.make} {vehicle_info.model}: "
        response += NHTSAApi.format_recalls_for_speech(recalls)
        
        # Log this check in session
        if self._session_id:
            self._session_manager.add_message(
                self._session_id, 
                "system", 
                f"Recall check performed. Found {len(recalls)} recalls.",
                {"vin": target_vin, "recall_count": len(recalls)}
            )
        
        return response
    
    @llm.function_tool(description="Get the details of the current car")
    async def get_car_details(self):
        logger.info("get car details")
        if not self.has_car():
            return "No vehicle is currently loaded. Please provide a VIN first."
        return f"The car details are: {self.get_car_str()}"
    
    @llm.function_tool(description="Create a new car profile in the system. If the VIN was just looked up, vehicle details are auto-filled. Always ask for owner_name and mileage before calling this.")
    async def create_car(
        self, 
        owner_name: Annotated[str, "The name of the vehicle owner - REQUIRED, must ask user"],
        mileage: Annotated[int, "The current mileage of the vehicle - REQUIRED, must ask user"],
        vin: Annotated[str, "The VIN of the car (optional if just looked up)"] = None,
        make: Annotated[str, "The make of the car (optional if just looked up)"] = None,
        model: Annotated[str, "The model of the car (optional if just looked up)"] = None,
        year: Annotated[int, "The year of the car (optional if just looked up)"] = None,
        owner_phone: Annotated[str, "The phone number of the owner"] = "",
    ):
        # Use pending vehicle info if available and params not provided
        if self._pending_vehicle:
            vin = vin or self._pending_vehicle.get("vin")
            make = make or self._pending_vehicle.get("make")
            model = model or self._pending_vehicle.get("model")
            year = year or self._pending_vehicle.get("year")
        
        # Validate required fields
        if not vin or not make or not model or not year:
            return "I need the VIN, make, model, and year to create a profile. Please provide the VIN first so I can look up the vehicle details."
        
        if not owner_name:
            return "I need your name to create the profile. What name should I register this vehicle under?"
        
        logger.info("create car - vin: %s, make: %s, model: %s, year: %s, owner: %s, mileage: %s", 
                    vin, make, model, year, owner_name, mileage)
        
        # Clean VIN
        vin = vin.upper().replace(" ", "").replace("-", "")
        
        try:
            result = DB.create_car(vin, make, model, year, mileage, owner_name, owner_phone)
            
            self._car_details = {
                CarDetails.VIN: result.vin,
                CarDetails.Make: result.make,
                CarDetails.Model: result.model,
                CarDetails.Year: result.year,
                CarDetails.Mileage: result.mileage,
                CarDetails.Owner: result.owner_name
            }
            
            # Clear pending vehicle
            self._pending_vehicle = None
            
            # Link to session
            if self._session_id:
                self._session_manager.link_vehicle_to_session(self._session_id, vin)
            
            logger.info("Successfully created car: %s", result)
            return f"I've created a profile for your {year} {make} {model}, registered to {owner_name} with {mileage:,} miles. How can I help you today?"
        except Exception as e:
            logger.error("Error creating car: %s", e, exc_info=True)
            return f"There was an issue creating the vehicle profile. The VIN might already exist in our system."
    
    @llm.function_tool(description="Update the mileage for the current vehicle")
    async def update_mileage(
        self, 
        mileage: Annotated[int, "The new mileage reading"]
    ):
        """Update vehicle mileage"""
        if not self.has_car():
            return "I need to look up your vehicle first. What's your VIN?"
        
        vin = self._car_details[CarDetails.VIN]
        success = DB.update_mileage(vin, mileage)
        
        if success:
            self._car_details[CarDetails.Mileage] = mileage
            return f"I've updated your mileage to {mileage:,} miles."
        return "There was an issue updating the mileage."
        
    def has_car(self):
        return self._car_details[CarDetails.VIN] != ""