from livekit.agents import llm
import enum
from typing import Annotated
import logging
from db_driver import DatabaseDriver

logger = logging.getLogger("user-data")
logger.setLevel(logging.INFO)

DB = DatabaseDriver()

class CarDetails(enum.Enum):
    VIN = "vin"
    Make = "make"
    Model = "model"
    Year = "year"
    

class AssistantFnc:
    def __init__(self):
        self._car_details = {
            CarDetails.VIN: "",
            CarDetails.Make: "",
            CarDetails.Model: "",
            CarDetails.Year: ""
        }
    
    def get_car_str(self):
        car_str = ""
        for key, value in self._car_details.items():
            car_str += f"{key.value}: {value}\n"
            
        return car_str
    
    @llm.function_tool(description="lookup a car by its vin")
    async def lookup_car(self, vin: Annotated[str, "The vin of the car to lookup"]):
        logger.info("lookup car - vin: %s", vin)
        
        result = DB.get_car_by_vin(vin)
        if result is None:
            logger.info("Car not found for VIN: %s", vin)
            return "Car not found"
        
        self._car_details = {
            CarDetails.VIN: result.vin,
            CarDetails.Make: result.make,
            CarDetails.Model: result.model,
            CarDetails.Year: result.year
        }
        
        logger.info("Successfully looked up car: %s", result)
        return f"The car details are: {self.get_car_str()}"
    
    @llm.function_tool(description="get the details of the current car")
    async def get_car_details(self):
        logger.info("get car details")
        return f"The car details are: {self.get_car_str()}"
    
    @llm.function_tool(description="create a new car record")
    async def create_car(
        self, 
        vin: Annotated[str, "The vin of the car"],
        make: Annotated[str, "The make of the car"],
        model: Annotated[str, "The model of the car"],
        year: Annotated[int, "The year of the car"]
    ):
        logger.info("create car - vin: %s, make: %s, model: %s, year: %s", vin, make, model, year)
        
        try:
            result = DB.create_car(vin, make, model, year)
            
            self._car_details = {
                CarDetails.VIN: result.vin,
                CarDetails.Make: result.make,
                CarDetails.Model: result.model,
                CarDetails.Year: result.year
            }
            
            logger.info("Successfully created car: %s", result)
            return "car created successfully!"
        except Exception as e:
            logger.error("Error creating car: %s", e, exc_info=True)
            return f"Failed to create car: {str(e)}"
        
    def has_car(self):
        return self._car_details[CarDetails.VIN] != ""