"""
NHTSA (National Highway Traffic Safety Administration) API Integration
Free API for vehicle recalls and safety information

Note: This API is for individual lookups, not bulk operations.
For a voice AI handling one customer at a time, this is appropriate usage.
"""

import aiohttp
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass


NHTSA_BASE_URL = "https://api.nhtsa.gov"
VPIC_BASE_URL = "https://vpic.nhtsa.dot.gov/api"


@dataclass
class RecallInfo:
    campaign_number: str
    component: str
    summary: str
    consequence: str
    remedy: str
    manufacturer: str
    report_date: str


@dataclass
class VehicleInfo:
    make: str
    model: str
    year: int
    vehicle_type: str
    plant_country: str


class NHTSAApi:
    """Interface for NHTSA vehicle safety APIs"""
    
    @staticmethod
    async def decode_vin(vin: str) -> Optional[VehicleInfo]:
        """Decode a VIN to get vehicle information"""
        # Clean the VIN
        vin = vin.upper().strip().replace(" ", "").replace("-", "")
        
        if len(vin) != 17:
            return None
        # Use vPIC API for VIN decode
        url = f"{VPIC_BASE_URL}/vehicles/DecodeVinValues/{vin}?format=json"
        headers = {
            "User-Agent": "Voice-AI-Agent/1.0 (+https://example.com/contact)",
            "Accept": "application/json",
        }
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                # Simple retry on 403/429
                for attempt in range(2):
                    try:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            if response.status in (403, 429):
                                if attempt == 0:
                                    await asyncio.sleep(0.5)
                                    continue
                                logging.warning(f"[vPIC] Decode VIN rate/forbidden status {response.status}")
                                return None
                            if response.status != 200:
                                logging.warning(f"[vPIC] API returned status {response.status}")
                                return None
                            data = await response.json()
                            results = data.get("Results", [])
                            if not results:
                                return None
                            result = results[0]
                            year_str = result.get("ModelYear", "0") or "0"
                            try:
                                year = int(year_str)
                            except ValueError:
                                year = 0
                            return VehicleInfo(
                                make=(result.get('Make') or 'Unknown').strip(),
                                model=(result.get("Model") or "Unknown").strip(),
                                year=year,
                                vehicle_type=(result.get("VehicleType") or "Unknown").strip(),
                                plant_country=(result.get("PlantCountry") or "Unknown").strip()
                            )
                    except aiohttp.ClientError as e:
                        if attempt == 0:
                            await asyncio.sleep(0.5)
                            continue
                        print(f"Network error: {e}")
                        return None
        except Exception as e:
            print(f" Unexpected error: {e}")
            return None
    
    @staticmethod
    async def get_recalls_by_vehicle(make: str, model: str, year: int) -> list[RecallInfo]:
        """Get recalls for a specific vehicle"""
        # URL encode the make and model
        import urllib.parse
        make_encoded = urllib.parse.quote(make)
        model_encoded = urllib.parse.quote(model)
        
        url = f"{NHTSA_BASE_URL}/recalls/recallsByVehicle?make={make_encoded}&model={model_encoded}&modelYear={year}"
        headers = {
            "User-Agent": "Voice-AI-Agent/1.0 (+https://example.com/contact)",
            "Accept": "application/json",
        }
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logging.warning(f"[NHTSA] Recalls API returned status {response.status}")
                        return []
                    
                    data = await response.json()
                    results = data.get("results", [])
                    
                    recalls = []
                    for item in results:
                        recalls.append(RecallInfo(
                            campaign_number=item.get("NHTSACampaignNumber", "N/A"),
                            component=item.get("Component", "N/A"),
                            summary=item.get("Summary", "No summary available"),
                            consequence=item.get("Consequence", "N/A"),
                            remedy=item.get("Remedy", "Contact dealer"),
                            manufacturer=item.get("Manufacturer", "N/A"),
                            report_date=item.get("ReportReceivedDate", "N/A")
                        ))
                    
                    return recalls
        except aiohttp.ClientError as e:
            logging.error(f"[NHTSA] Network error fetching recalls: {e}")
            return []
        except Exception as e:
            logging.error(f"[NHTSA] Unexpected error fetching recalls: {e}")
            return []
    
    
    @staticmethod
    def format_recalls_for_speech(recalls: list[RecallInfo]) -> str:
        """Format recall information for voice output"""
        if not recalls:
            return "Great news! I found no open recalls for your vehicle."
        
        count = len(recalls)
        response = f"I found {count} recall{'s' if count > 1 else ''} for your vehicle. "
        
        # Summarize first 3 recalls for voice
        for i, recall in enumerate(recalls[:3], 1):
            summary = recall.summary[:100] + "..." if len(recall.summary) > 100 else recall.summary
            response += f"Recall {i}: {recall.component}. {summary} "
        
        if count > 3:
            response += f"There are {count - 3} more recalls. Would you like me to provide more details?"
        
        return response
    
    @staticmethod
    async def get_recalls_by_vin(vin: str) -> tuple[Optional[VehicleInfo], list[RecallInfo]]:
        """Decode VIN and get recalls in one call"""
        vehicle_info = await NHTSAApi.decode_vin(vin)
    
        if not vehicle_info:
            return None, []
    
        recalls = await NHTSAApi.get_recalls_by_vehicle(
            vehicle_info.make, 
            vehicle_info.model, 
            vehicle_info.year
        )
    
        return vehicle_info, recalls


# Test function
async def test_nhtsa():
    """Test NHTSA API functionality with a single sample VIN"""
    sample_vin = "1FA6P8CF0F5391308"  # Example: 2015 Ford Mustang (results may vary)
    print(f"Testing VIN decode for: {sample_vin}")
    vehicle_info = await NHTSAApi.decode_vin(sample_vin)
    if vehicle_info:
        print(f" Vehicle: {vehicle_info.year} {vehicle_info.make} {vehicle_info.model}")
        recalls = await NHTSAApi.get_recalls_by_vehicle(vehicle_info.make, vehicle_info.model, vehicle_info.year)
        print(f" Recalls found: {len(recalls)}")
        print('--> Example Recall Record  : \n', recalls[0])
    else:
        print(" Could not decode VIN (may be invalid or API unavailable)")
    

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_nhtsa())
