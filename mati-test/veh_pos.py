from google.transit import gtfs_realtime_pb2
import requests


def main():
    # # Load GTFS-RT file (e.g., "vehicle_positions.bin")
    # feed = gtfs_realtime_pb2.FeedMessage()

    # with open("vehicle_positions.bin", "rb") as f:
    #     feed.ParseFromString(f.read())

    # print("GTFS-RT header:", feed.header)

    # for entity in feed.entity:
    #     if entity.HasField("vehicle"):
    #         v = entity.vehicle
    #         print("Vehicle ID:", v.vehicle.id)
    #         print("Trip ID:", v.trip.trip_id)
    #         print("Latitude:", v.position.latitude)
    #         print("Longitude:", v.position.longitude)
    #         print("Timestamp:", v.timestamp)
    #         print("---")


    
    url = "https://otwarte.miasto.lodz.pl/wp-content/uploads/2025/06/vehicle_positions.bin"  # replace with real feed
    feed = gtfs_realtime_pb2.FeedMessage()

    response = requests.get(url)
    print(response)
    print(response.content)
    
    feed.ParseFromString(response.content)

    print("GTFS-RT header:", feed.header)

    for entity in feed.entity:
        if entity.HasField("vehicle"):
            v = entity.vehicle
            print("Vehicle ID:", v.vehicle.id)
            print("Trip ID:", v.trip.trip_id)
            print("Latitude:", v.position.latitude)
            print("Longitude:", v.position.longitude)
            print("Timestamp:", v.timestamp)
            print("---")

    # for entity in feed.entity:
    #     if entity.HasField("trip_update"):
    #         tu = entity.trip_update
    #         print("Trip:", tu.trip.trip_id)
    #         for stu in tu.stop_time_update:
    #             print(" Stop:", stu.stop_id, "Delay:", stu.arrival.delay)

if __name__ == "__main__":
    main()