import sunspec.core.client as client
import prometheus_client as prom
from datetime import datetime
import time
import signal
import os

# Create a metric to track time spent and requests made.
req_summary = prom.Summary('python_my_req_example', 'Time spent processing a request')
SunSpecDevice = client.SunSpecClientDevice

gauges = {}

class GracefulKiller:
  kill_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self,signum, frame):
    self.kill_now = True


# Decorate function with metric.
@req_summary.time()
def process_request():
    # Read device status
    SunSpecDevice.read()
    
    # Update Gauges
    for model in gauges:
        for param in gauges[model]:
            point = SunSpecDevice[model].model.points[param]
            gauges[model][param].labels(model, point.point_type.units).set(SunSpecDevice[model][param] or 0)

#################################################################
# Main
#################################################################
if __name__ == '__main__':
    killer = GracefulKiller()

    # Get ENV parameters
    target_addr = os.environ.get('TARGET_IP') or '192.168.1.6'

    # Target port
    try:
        target_port = int(os.environ.get('TARGET_PORT'))
    except:
        target_port = 502

    # Listen port
    try:
        listen_port = int(os.environ.get('LISTEN_PORT'))
    except:
        listen_port = 8080

    # Scrape interval
    try:
        scrape_interval = int(os.environ.get('SCRAPE_INTERVAL'))
    except:
        scrape_interval = 1

    # Start up the server to expose the metrics.
    print("Starting metrics server on port ", listen_port)
    try:
        prom.start_http_server(listen_port)
        print("Metrics server started")
    except Exception as e:
        print(str(e))
        exit()
    
    # Main loop
    while not killer.kill_now:
        now = datetime.now() # current date and time
        date_time = now.strftime("[%Y-%m-%d %H:%M:%S]")

        # Try to connect to target
        print(date_time, "Connecting to SunSpec target on", target_addr, "port", target_port)
        try:
            SunSpecDevice = client.SunSpecClientDevice(client.TCP, 1, ipaddr=target_addr, ipport=target_port)
            print("Connected to SunSpec target")
            
            # Read device once to check capabilities
            SunSpecDevice.read()
           
            # Get all available parameters in device and create a gauge for each one
            for model in SunSpecDevice.models:
                for param in SunSpecDevice.inverter.model.points:
                    if not model in gauges:
                        gauges[model] = {}
                    if not param in gauges[model]:
                        point = SunSpecDevice[model].model.points[param]
                        if SunSpecDevice[model][param] != None:
                            gauge = prom.Gauge( name=param, \
                                documentation = point.point_type.description, \
                                unit = point.point_type.units, \
                                labelnames = ['model', 'unit'] )
                            gauges[model][param] = gauge

            try:
                while not killer.kill_now:
                    process_request()
                    time.sleep(scrape_interval)
            except Exception as e:
                print(str(e))
                SunSpecDevice.close()
                print(date_time, "Closed connection to SunSpec server")
            
        except Exception as e:
            print(str(e))
            time.sleep(1)
        
    try:
        SunSpecDevice.close()
        print(date_time, "Closed connection to SunSpec server")
    except:
        None
    
    print(date_time, "Exited")
