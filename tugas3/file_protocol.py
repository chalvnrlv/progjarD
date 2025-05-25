import json
import logging
import base64
from file_interface import FileInterface

class FileProtocol:
    def __init__(self):
        self.file = FileInterface()
    
    def proses_string(self, string_datamasuk):
        # Batasi log untuk data besar
        preview = string_datamasuk[:50] + "..." if len(string_datamasuk) > 50 else string_datamasuk
        logging.warning(f"Processing command: {preview}")
        
        try:
            # Try to parse as JSON first (for UPLOAD command)
            try:
                command_data = json.loads(string_datamasuk)
                if isinstance(command_data, dict) and "command" in command_data:
                    return self.handle_json_command(command_data)
            except json.JSONDecodeError:
                pass
            
            # Handle simple string commands (LIST, GET, DELETE)
            parts = string_datamasuk.strip().split(' ', 1)
            command = parts[0].strip().lower()
            params = parts[1] if len(parts) > 1 else ""
            
            if command == "list":
                return json.dumps(self.file.list([]))
            elif command == "get":
                if not params:
                    return json.dumps({"status": "ERROR", "data": "Nama file diperlukan"})
                return json.dumps(self.file.get([params.strip()]))
            elif command == "delete":
                if not params:
                    return json.dumps({"status": "ERROR", "data": "Nama file diperlukan"})
                return json.dumps(self.file.delete([params.strip()]))
            elif command == "upload":
                # Handle old-style upload (fallback)
                return json.dumps({"status": "ERROR", "data": "Format upload tidak valid. Gunakan JSON format."})
            else:
                return json.dumps({"status": "ERROR", "data": "Command tidak valid"})
                
        except Exception as e:
            logging.error(f"Error: {str(e)}")
            return json.dumps({"status": "ERROR", "data": f"Terjadi kesalahan server: {str(e)}"})
    
    def handle_json_command(self, command_data):
        """Handle JSON-formatted commands"""
        try:
            command = command_data.get("command", "").lower()
            
            if command == "upload":
                filename = command_data.get("filename", "")
                filedata = command_data.get("filedata", "")
                
                if not filename or not filedata:
                    return json.dumps({"status": "ERROR", "data": "Parameter tidak lengkap"})
                
                # Validate base64 data
                try:
                    # Test decode to validate base64
                    decoded_data = base64.b64decode(filedata)
                    logging.warning(f"Upload file: {filename}, size: {len(decoded_data)} bytes")
                except Exception as e:
                    return json.dumps({"status": "ERROR", "data": f"Data base64 tidak valid: {str(e)}"})
                
                return json.dumps(self.file.upload([filename, filedata]))
            else:
                return json.dumps({"status": "ERROR", "data": "Command JSON tidak valid"})
                
        except Exception as e:
            logging.error(f"Error handling JSON command: {str(e)}")
            return json.dumps({"status": "ERROR", "data": f"Error processing JSON command: {str(e)}"})

if __name__ == '__main__':
    # contoh pemakaian
    fp = FileProtocol()
    print(fp.proses_string("LIST"))
    print(fp.proses_string("GET pokijan.jpg"))
