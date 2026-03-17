from pythonosc.udp_client import SimpleUDPClient

class OSCSender:
    def __init__(self, ip: str, port: int, base_address: str):
        self.client = SimpleUDPClient(ip, port)
        self.base_address = base_address
        print(f"[Sender] Prêt à envoyer en OSC vers {ip}:{port}{base_address}/...")

    def send_dict(self, blendshapes_dict: dict):
        """Envoie chaque élément du dictionnaire sur son propre canal OSC."""
        for shape_name, value in blendshapes_dict.items():
            # Crée l'adresse finale, ex: /blendshapes/EyeBlinkLeft
            address = f"{self.base_address}/{shape_name}"
            self.client.send_message(address, float(value))