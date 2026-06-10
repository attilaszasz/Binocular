import asyncio
from binocular.scraping.client import ScrapeClient

async def main():
    client = ScrapeClient()
    
    def sync_check_firmware(url, model, http_client):
        print("sync_check_firmware started")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            resp = loop.run_until_complete(http_client.get(url))
            print("Response status:", resp.status_code)
            # Do NOT close the loop here
        except Exception as e:
            print("Option A failed:", e)
            
    await asyncio.to_thread(sync_check_firmware, "https://alphauniverse.com/firmware/", "A7IV", client)
    print("Closing client")
    await client.close()
    print("Client closed successfully")

if __name__ == "__main__":
    asyncio.run(main())
