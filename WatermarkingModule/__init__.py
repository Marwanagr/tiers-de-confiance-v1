# On importe la classe Watermarker depuis le fichier local engine.py
from WatermarkingModule.engine import Watermarker

# on définit une version pour le module (optionnel)
__version__ = "1.0.0"


# Ce que l'utilisateur voit quand il fait help(WatermarkingModule)
__all__ = ["Watermarker"]