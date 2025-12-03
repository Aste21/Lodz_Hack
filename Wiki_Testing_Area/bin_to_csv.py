"""
Skrypt do konwersji plików binarnych GTFS Realtime (.bin) do formatu CSV
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import struct

# Próba zaimportowania bibliotek GTFS Realtime
try:
    from google.transit import gtfs_realtime_pb2
    GTFS_REALTIME_AVAILABLE = True
except ImportError:
    GTFS_REALTIME_AVAILABLE = False
    print("⚠ Biblioteka gtfs-realtime-bindings nie jest zainstalowana.")
    print("  Uruchom: pip install gtfs-realtime-bindings")
    print("  Skrypt będzie próbował parsować ręcznie.\n")


def read_binary_file(filepath: Path) -> bytes:
    """Czyta plik binarny"""
    with open(filepath, 'rb') as f:
        return f.read()


def parse_protobuf_like_data(data: bytes) -> Dict:
    """
    Próbuje sparsować dane jako protobuf lub JSON
    Jeśli to nie protobuf, próbuje jako JSON lub zwraca surowe dane
    """
    # Próba 1: Sprawdź czy to JSON
    try:
        text = data.decode('utf-8')
        return json.loads(text)
    except:
        pass
    
    # Próba 2: Sprawdź czy to może być protobuf (sprawdź magic bytes)
    # GTFS Realtime protobuf zwykle zaczyna się od określonych bajtów
    
    # Zwróć surowe dane jako hex i struktura
    return {
        'raw_hex': data.hex(),
        'raw_bytes': list(data),
        'size': len(data),
        'first_100_bytes_hex': data[:100].hex() if len(data) > 100 else data.hex()
    }


def extract_protobuf_fields(data: bytes) -> List[Dict]:
    """
    Próbuje wyekstrahować pola z danych protobuf
    Protobuf używa tagów i typów, więc próbujemy je zidentyfikować
    """
    results = []
    i = 0
    
    while i < len(data):
        try:
            # Protobuf wire types:
            # 0: Varint
            # 1: 64-bit
            # 2: Length-delimited
            # 5: 32-bit
            
            if i + 1 > len(data):
                break
                
            byte = data[i]
            field_number = byte >> 3
            wire_type = byte & 0x7
            
            field_info = {
                'offset': i,
                'field_number': field_number,
                'wire_type': wire_type,
                'wire_type_name': ['Varint', '64-bit', 'Length-delimited', 'Start group', 'End group', '32-bit', 'Unknown'][wire_type] if wire_type < 7 else 'Unknown',
                'raw_byte': byte
            }
            
            i += 1
            
            # Próbuj odczytać wartość w zależności od typu
            if wire_type == 0:  # Varint
                value, bytes_read = read_varint(data, i)
                field_info['value'] = value
                field_info['value_bytes'] = bytes_read
                i += bytes_read
            elif wire_type == 1:  # 64-bit
                if i + 8 <= len(data):
                    field_info['value'] = struct.unpack('<d', data[i:i+8])[0]
                    i += 8
            elif wire_type == 2:  # Length-delimited
                length, bytes_read = read_varint(data, i)
                field_info['length'] = length
                if i + bytes_read + length <= len(data):
                    field_info['value'] = data[i+bytes_read:i+bytes_read+length].hex()
                    i += bytes_read + length
                else:
                    break
            elif wire_type == 5:  # 32-bit
                if i + 4 <= len(data):
                    field_info['value'] = struct.unpack('<f', data[i:i+4])[0]
                    i += 4
            else:
                i += 1
            
            results.append(field_info)
            
            if i >= len(data) or len(results) > 1000:  # Limit dla bezpieczeństwa
                break
                
        except Exception as e:
            field_info = {
                'offset': i,
                'error': str(e),
                'raw_byte': data[i] if i < len(data) else None
            }
            results.append(field_info)
            i += 1
            if i >= len(data):
                break
    
    return results


def read_varint(data: bytes, start: int) -> tuple:
    """Czyta varint z danych"""
    result = 0
    shift = 0
    bytes_read = 0
    
    for i in range(start, min(start + 10, len(data))):  # Varint max 10 bajtów
        byte = data[i]
        result |= (byte & 0x7F) << shift
        bytes_read += 1
        if not (byte & 0x80):
            break
        shift += 7
    
    return result, bytes_read


def parse_gtfs_realtime(data: bytes, file_type: str) -> Optional[Dict]:
    """Parsuje dane GTFS Realtime używając oficjalnej biblioteki"""
    if not GTFS_REALTIME_AVAILABLE:
        return None
    
    try:
        feed_message = gtfs_realtime_pb2.FeedMessage()
        feed_message.ParseFromString(data)
        
        result = {
            'header': {
                'gtfs_realtime_version': feed_message.header.gtfs_realtime_version,
                'timestamp': feed_message.header.timestamp,
                'incrementality': feed_message.header.incrementality
            },
            'entities': []
        }
        
        for entity in feed_message.entity:
            entity_data = {
                'id': entity.id,
                'is_deleted': entity.is_deleted,
            }
            
            # Trip Updates
            if entity.HasField('trip_update'):
                tu = entity.trip_update
                entity_data['trip_update'] = {
                    'trip': {
                        'trip_id': tu.trip.trip_id if tu.trip.trip_id else None,
                        'route_id': tu.trip.route_id if tu.trip.route_id else None,
                        'direction_id': tu.trip.direction_id if tu.trip.HasField('direction_id') else None,
                        'start_time': tu.trip.start_time if tu.trip.start_time else None,
                        'start_date': tu.trip.start_date if tu.trip.start_date else None,
                        'schedule_relationship': tu.trip.schedule_relationship
                    },
                    'vehicle': {
                        'id': tu.vehicle.id if tu.vehicle.id else None,
                        'label': tu.vehicle.label if tu.vehicle.label else None,
                        'license_plate': tu.vehicle.license_plate if tu.vehicle.license_plate else None
                    } if tu.HasField('vehicle') else None,
                    'stop_time_updates': []
                }
                
                for stu in tu.stop_time_update:
                    stu_data = {
                        'stop_sequence': stu.stop_sequence if stu.HasField('stop_sequence') else None,
                        'stop_id': stu.stop_id if stu.stop_id else None,
                        'arrival': {
                            'delay': stu.arrival.delay if stu.arrival.HasField('delay') else None,
                            'time': stu.arrival.time if stu.arrival.HasField('time') else None,
                            'uncertainty': stu.arrival.uncertainty if stu.arrival.HasField('uncertainty') else None
                        } if stu.HasField('arrival') else None,
                        'departure': {
                            'delay': stu.departure.delay if stu.departure.HasField('delay') else None,
                            'time': stu.departure.time if stu.departure.HasField('time') else None,
                            'uncertainty': stu.departure.uncertainty if stu.departure.HasField('uncertainty') else None
                        } if stu.HasField('departure') else None,
                        'schedule_relationship': stu.schedule_relationship
                    }
                    entity_data['trip_update']['stop_time_updates'].append(stu_data)
            
            # Vehicle Positions
            if entity.HasField('vehicle'):
                vp = entity.vehicle
                entity_data['vehicle_position'] = {
                    'trip': {
                        'trip_id': vp.trip.trip_id if vp.trip.trip_id else None,
                        'route_id': vp.trip.route_id if vp.trip.route_id else None,
                        'direction_id': vp.trip.direction_id if vp.trip.HasField('direction_id') else None,
                        'start_time': vp.trip.start_time if vp.trip.start_time else None,
                        'start_date': vp.trip.start_date if vp.trip.start_date else None,
                        'schedule_relationship': vp.trip.schedule_relationship
                    } if vp.HasField('trip') else None,
                    'vehicle': {
                        'id': vp.vehicle.id if vp.vehicle.id else None,
                        'label': vp.vehicle.label if vp.vehicle.label else None,
                        'license_plate': vp.vehicle.license_plate if vp.vehicle.license_plate else None
                    } if vp.HasField('vehicle') else None,
                    'position': {
                        'latitude': vp.position.latitude if vp.position.HasField('latitude') else None,
                        'longitude': vp.position.longitude if vp.position.HasField('longitude') else None,
                        'bearing': vp.position.bearing if vp.position.HasField('bearing') else None,
                        'odometer': vp.position.odometer if vp.position.HasField('odometer') else None,
                        'speed': vp.position.speed if vp.position.HasField('speed') else None
                    } if vp.HasField('position') else None,
                    'current_stop_sequence': vp.current_stop_sequence if vp.HasField('current_stop_sequence') else None,
                    'stop_id': vp.stop_id if vp.stop_id else None,
                    'current_status': vp.current_status,
                    'timestamp': vp.timestamp if vp.HasField('timestamp') else None,
                    'congestion_level': vp.congestion_level,
                    'occupancy_status': vp.occupancy_status
                }
            
            # Alerts
            if entity.HasField('alert'):
                alert = entity.alert
                entity_data['alert'] = {
                    'active_period': [
                        {
                            'start': ap.start if ap.HasField('start') else None,
                            'end': ap.end if ap.HasField('end') else None
                        }
                        for ap in alert.active_period
                    ],
                    'informed_entity': [
                        {
                            'agency_id': ie.agency_id if ie.agency_id else None,
                            'route_id': ie.route_id if ie.route_id else None,
                            'route_type': ie.route_type if ie.HasField('route_type') else None,
                            'trip': {
                                'trip_id': ie.trip.trip_id if ie.trip.trip_id else None,
                                'route_id': ie.trip.route_id if ie.trip.route_id else None,
                                'direction_id': ie.trip.direction_id if ie.trip.HasField('direction_id') else None,
                                'start_time': ie.trip.start_time if ie.trip.start_time else None,
                                'start_date': ie.trip.start_date if ie.trip.start_date else None,
                                'schedule_relationship': ie.trip.schedule_relationship
                            } if ie.HasField('trip') else None,
                            'stop_id': ie.stop_id if ie.stop_id else None
                        }
                        for ie in alert.informed_entity
                    ],
                    'cause': alert.cause,
                    'effect': alert.effect,
                    'url': {
                        'translation': [
                            {
                                'text': t.text if t.text else None,
                                'language': t.language if t.language else None
                            }
                            for t in alert.url.translation
                        ]
                    } if alert.HasField('url') else None,
                    'header_text': {
                        'translation': [
                            {
                                'text': t.text if t.text else None,
                                'language': t.language if t.language else None
                            }
                            for t in alert.header_text.translation
                        ]
                    } if alert.HasField('header_text') else None,
                    'description_text': {
                        'translation': [
                            {
                                'text': t.text if t.text else None,
                                'language': t.language if t.language else None
                            }
                            for t in alert.description_text.translation
                        ]
                    } if alert.HasField('description_text') else None
                }
            
            result['entities'].append(entity_data)
        
        return result
    except Exception as e:
        print(f"    Błąd parsowania GTFS Realtime: {e}")
        return None


def analyze_binary_file(filepath: Path) -> Dict:
    """Analizuje plik binarny i zwraca szczegółowe informacje"""
    print(f"\nAnalizowanie pliku: {filepath.name}")
    print(f"Rozmiar: {filepath.stat().st_size} bajtów")
    
    data = read_binary_file(filepath)
    
    # Podstawowa analiza
    analysis = {
        'filename': filepath.name,
        'size_bytes': len(data),
        'first_bytes_hex': data[:50].hex() if len(data) > 50 else data.hex(),
        'first_bytes_decimal': list(data[:50]) if len(data) > 50 else list(data),
    }
    
    # Próba parsowania jako GTFS Realtime
    print("  Próba parsowania jako GTFS Realtime...")
    gtfs_data = parse_gtfs_realtime(data, filepath.name)
    if gtfs_data:
        analysis['gtfs_realtime'] = gtfs_data
        analysis['is_gtfs_realtime'] = True
        print(f"  ✓ Plik jest w formacie GTFS Realtime!")
        print(f"    Wersja: {gtfs_data['header']['gtfs_realtime_version']}")
        print(f"    Liczba encji: {len(gtfs_data['entities'])}")
    else:
        analysis['is_gtfs_realtime'] = False
    
    # Próba parsowania jako protobuf (ręcznie)
    if not analysis.get('is_gtfs_realtime'):
        print("  Próba parsowania jako protobuf (ręcznie)...")
        try:
            protobuf_fields = extract_protobuf_fields(data)
            analysis['protobuf_fields'] = protobuf_fields[:100]  # Pierwsze 100 pól
            analysis['total_protobuf_fields'] = len(protobuf_fields)
            print(f"  Znaleziono {len(protobuf_fields)} potencjalnych pól protobuf")
        except Exception as e:
            print(f"  Błąd parsowania protobuf: {e}")
            analysis['protobuf_error'] = str(e)
    
    # Próba jako JSON
    try:
        text = data.decode('utf-8')
        json_data = json.loads(text)
        analysis['is_json'] = True
        analysis['json_data'] = json_data
        print("  ✓ Plik jest w formacie JSON")
    except:
        analysis['is_json'] = False
    
    return analysis


def save_to_csv(analysis: Dict, output_dir: Path):
    """Zapisuje analizę do plików CSV"""
    filename = analysis['filename']
    base_name = filename.replace('.bin', '')
    
    # 1. Podstawowe informacje
    basic_info = pd.DataFrame([{
        'filename': analysis['filename'],
        'size_bytes': analysis['size_bytes'],
        'first_bytes_hex': analysis['first_bytes_hex'],
        'is_json': analysis.get('is_json', False),
        'is_gtfs_realtime': analysis.get('is_gtfs_realtime', False),
        'total_protobuf_fields': analysis.get('total_protobuf_fields', 0)
    }])
    basic_info.to_csv(output_dir / f"{base_name}_info.csv", index=False)
    print(f"  ✓ Zapisano {base_name}_info.csv")
    
    # 2. GTFS Realtime data (jeśli jest)
    if analysis.get('is_gtfs_realtime') and 'gtfs_realtime' in analysis:
        gtfs = analysis['gtfs_realtime']
        
        # Header
        header_df = pd.DataFrame([gtfs['header']])
        header_df.to_csv(output_dir / f"{base_name}_header.csv", index=False)
        print(f"  ✓ Zapisano {base_name}_header.csv")
        
        # Entities - rozwijamy do płaskiej struktury
        entities_list = []
        for entity in gtfs['entities']:
            entity_row = {
                'entity_id': entity['id'],
                'is_deleted': entity['is_deleted'],
                'has_trip_update': 'trip_update' in entity,
                'has_vehicle_position': 'vehicle_position' in entity,
                'has_alert': 'alert' in entity
            }
            
            # Trip Update
            if 'trip_update' in entity:
                tu = entity['trip_update']
                entity_row.update({
                    'tu_trip_id': tu['trip']['trip_id'] if tu['trip'] else None,
                    'tu_route_id': tu['trip']['route_id'] if tu['trip'] else None,
                    'tu_direction_id': tu['trip']['direction_id'] if tu['trip'] else None,
                    'tu_start_time': tu['trip']['start_time'] if tu['trip'] else None,
                    'tu_vehicle_id': tu['vehicle']['id'] if tu['vehicle'] else None,
                    'tu_stop_updates_count': len(tu['stop_time_updates'])
                })
            
            # Vehicle Position
            if 'vehicle_position' in entity:
                vp = entity['vehicle_position']
                entity_row.update({
                    'vp_trip_id': vp['trip']['trip_id'] if vp['trip'] else None,
                    'vp_route_id': vp['trip']['route_id'] if vp['trip'] else None,
                    'vp_vehicle_id': vp['vehicle']['id'] if vp['vehicle'] else None,
                    'vp_latitude': vp['position']['latitude'] if vp['position'] else None,
                    'vp_longitude': vp['position']['longitude'] if vp['position'] else None,
                    'vp_speed': vp['position']['speed'] if vp['position'] else None,
                    'vp_bearing': vp['position']['bearing'] if vp['position'] else None,
                    'vp_current_stop_id': vp['stop_id'],
                    'vp_current_status': vp['current_status'],
                    'vp_timestamp': vp['timestamp']
                })
            
            # Alert
            if 'alert' in entity:
                alert = entity['alert']
                entity_row.update({
                    'alert_cause': alert['cause'],
                    'alert_effect': alert['effect'],
                    'alert_active_periods': len(alert['active_period']),
                    'alert_informed_entities': len(alert['informed_entity'])
                })
            
            entities_list.append(entity_row)
        
        if entities_list:
            entities_df = pd.DataFrame(entities_list)
            entities_df.to_csv(output_dir / f"{base_name}_entities.csv", index=False)
            print(f"  ✓ Zapisano {base_name}_entities.csv ({len(entities_df)} wierszy)")
        
        # Szczegółowe dane - Trip Updates
        if any('trip_update' in e for e in gtfs['entities']):
            tu_list = []
            for entity in gtfs['entities']:
                if 'trip_update' in entity:
                    tu = entity['trip_update']
                    for stu in tu['stop_time_updates']:
                        tu_row = {
                            'entity_id': entity['id'],
                            'trip_id': tu['trip']['trip_id'] if tu['trip'] else None,
                            'route_id': tu['trip']['route_id'] if tu['trip'] else None,
                            'stop_id': stu['stop_id'],
                            'stop_sequence': stu['stop_sequence'],
                            'arrival_delay': stu['arrival']['delay'] if stu['arrival'] else None,
                            'arrival_time': stu['arrival']['time'] if stu['arrival'] else None,
                            'departure_delay': stu['departure']['delay'] if stu['departure'] else None,
                            'departure_time': stu['departure']['time'] if stu['departure'] else None,
                            'schedule_relationship': stu['schedule_relationship']
                        }
                        tu_list.append(tu_row)
            
            if tu_list:
                tu_df = pd.DataFrame(tu_list)
                tu_df.to_csv(output_dir / f"{base_name}_trip_updates.csv", index=False)
                print(f"  ✓ Zapisano {base_name}_trip_updates.csv ({len(tu_df)} wierszy)")
        
        # Szczegółowe dane - Vehicle Positions
        if any('vehicle_position' in e for e in gtfs['entities']):
            vp_list = []
            for entity in gtfs['entities']:
                if 'vehicle_position' in entity:
                    vp = entity['vehicle_position']
                    vp_row = {
                        'entity_id': entity['id'],
                        'trip_id': vp['trip']['trip_id'] if vp['trip'] else None,
                        'route_id': vp['trip']['route_id'] if vp['trip'] else None,
                        'vehicle_id': vp['vehicle']['id'] if vp['vehicle'] else None,
                        'latitude': vp['position']['latitude'] if vp['position'] else None,
                        'longitude': vp['position']['longitude'] if vp['position'] else None,
                        'speed': vp['position']['speed'] if vp['position'] else None,
                        'bearing': vp['position']['bearing'] if vp['position'] else None,
                        'current_stop_id': vp['stop_id'],
                        'current_stop_sequence': vp['current_stop_sequence'],
                        'current_status': vp['current_status'],
                        'timestamp': vp['timestamp'],
                        'congestion_level': vp['congestion_level'],
                        'occupancy_status': vp['occupancy_status']
                    }
                    vp_list.append(vp_row)
            
            if vp_list:
                vp_df = pd.DataFrame(vp_list)
                vp_df.to_csv(output_dir / f"{base_name}_vehicle_positions.csv", index=False)
                print(f"  ✓ Zapisano {base_name}_vehicle_positions.csv ({len(vp_df)} wierszy)")
        
        # Szczegółowe dane - Alerts
        if any('alert' in e for e in gtfs['entities']):
            alert_list = []
            for entity in gtfs['entities']:
                if 'alert' in entity:
                    alert = entity['alert']
                    for ie in alert['informed_entity']:
                        alert_row = {
                            'entity_id': entity['id'],
                            'cause': alert['cause'],
                            'effect': alert['effect'],
                            'agency_id': ie['agency_id'],
                            'route_id': ie['route_id'],
                            'route_type': ie['route_type'],
                            'trip_id': ie['trip']['trip_id'] if ie['trip'] else None,
                            'stop_id': ie['stop_id']
                        }
                        alert_list.append(alert_row)
            
            if alert_list:
                alert_df = pd.DataFrame(alert_list)
                alert_df.to_csv(output_dir / f"{base_name}_alerts.csv", index=False)
                print(f"  ✓ Zapisano {base_name}_alerts.csv ({len(alert_df)} wierszy)")
    
    # 3. Pola protobuf (jeśli są i nie jest GTFS Realtime)
    if not analysis.get('is_gtfs_realtime') and 'protobuf_fields' in analysis and analysis['protobuf_fields']:
        protobuf_df = pd.DataFrame(analysis['protobuf_fields'])
        protobuf_df.to_csv(output_dir / f"{base_name}_protobuf_fields.csv", index=False)
        print(f"  ✓ Zapisano {base_name}_protobuf_fields.csv ({len(protobuf_df)} wierszy)")
    
    # 4. JSON data (jeśli jest)
    if analysis.get('is_json') and 'json_data' in analysis:
        # Spróbuj spłaszczyć JSON do DataFrame
        try:
            if isinstance(analysis['json_data'], dict):
                # Dla słowników, spróbuj stworzyć DataFrame
                json_df = pd.json_normalize(analysis['json_data'])
                json_df.to_csv(output_dir / f"{base_name}_json.csv", index=False)
                print(f"  ✓ Zapisano {base_name}_json.csv")
            elif isinstance(analysis['json_data'], list):
                json_df = pd.DataFrame(analysis['json_data'])
                json_df.to_csv(output_dir / f"{base_name}_json.csv", index=False)
                print(f"  ✓ Zapisano {base_name}_json.csv ({len(json_df)} wierszy)")
        except Exception as e:
            print(f"  ⚠ Nie udało się zapisać JSON do CSV: {e}")
            # Zapisz jako tekst JSON
            with open(output_dir / f"{base_name}_json.txt", 'w', encoding='utf-8') as f:
                json.dump(analysis['json_data'], f, indent=2, ensure_ascii=False)
            print(f"  ✓ Zapisano {base_name}_json.txt")


def main():
    """Główna funkcja"""
    print("=" * 60)
    print("KONWERSJA PLIKÓW BINARNYCH DO CSV")
    print("=" * 60)
    
    # Folder z plikami binarnymi
    base_dir = Path(__file__).parent
    output_dir = base_dir / "bin_csv_output"
    output_dir.mkdir(exist_ok=True)
    
    print(f"\nFolder wyjściowy: {output_dir}")
    
    # Znajdź wszystkie pliki .bin
    bin_files = list(base_dir.glob("*.bin"))
    
    if not bin_files:
        print("\n⚠ Nie znaleziono plików .bin w bieżącym folderze")
        return
    
    print(f"\nZnaleziono {len(bin_files)} plików .bin:")
    for f in bin_files:
        print(f"  - {f.name}")
    
    # Analizuj każdy plik
    for bin_file in bin_files:
        try:
            analysis = analyze_binary_file(bin_file)
            save_to_csv(analysis, output_dir)
        except Exception as e:
            print(f"\n✗ Błąd przy przetwarzaniu {bin_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✓ Konwersja zakończona!")
    print(f"Wszystkie pliki CSV zapisane w: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()

