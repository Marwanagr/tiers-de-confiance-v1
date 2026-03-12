import numpy as np
import cv2
import reedsolo
from . import utils

class Watermarker:
    def __init__(self, alpha=0.1, nsym=10, repetitions=3):
        self.alpha = alpha
        self.nsym = nsym
        self.repetitions = repetitions
        self.rs = reedsolo.RSCodec(nsym)
        self.zz = utils.zigzag_indices(8)
        all_pos = list(range(1, 40))
        self.pos_groups = [all_pos[i::3] for i in range(3)]

    def _prepare_dimensions(self, img):
        """Ajuste l'image pour qu'elle soit divisible par 8."""
        h, w = img.shape[:2]
        h_pad, w_pad = (h // 8) * 8, (w // 8) * 8
        if h != h_pad or w != w_pad:
            img = cv2.resize(img, (w_pad, h_pad))
        return img, h_pad, w_pad

    def encode(self, input_path, message, output_path):
            img = cv2.imread(input_path)
            if img is None: raise FileNotFoundError(f"Image non trouvée")
            
            host, h, w = self._prepare_dimensions(img)
            
            # Conversion PRO via OpenCV pour éviter les dérives de couleur
            ycrcb = cv2.cvtColor(host, cv2.COLOR_BGR2YCrCb)
            Y = ycrcb[:, :, 0].astype(np.float32) - 128
            
            # DCT
            dct_Y = np.zeros_like(Y)
            for i in range(0, h, 8):
                for j in range(0, w, 8):
                    dct_Y[i:i+8, j:j+8] = utils.dct2(Y[i:i+8, j:j+8])

            # Message
            msg_rs = self.rs.encode(message.encode('utf-8'))
            payload = len(msg_rs).to_bytes(2, byteorder='big') + msg_rs
            bits = utils.bytes_to_bits(payload)

            
            all_pos = list(range(10, 45)) 
            pos_groups = [all_pos[i::3] for i in range(3)]

            for r in range(self.repetitions):
                pos = pos_groups[r % 3]
                idx_bit = 0
                for i in range(0, h, 8):
                    for j in range(0, w, 8):
                        if idx_bit >= len(bits): break
                        bit = bits[idx_bit]
                        for p in pos:
                            u, v = self.zz[p]
                            
                            if bit == 1: dct_Y[i+u, j+v] += (15 * self.alpha)
                            else: dct_Y[i+u, j+v] -= (15 * self.alpha)
                        idx_bit += 1

            # Reconstruction
            Y_rec = np.zeros_like(Y)
            for i in range(0, h, 8):
                for j in range(0, w, 8):
                    Y_rec[i:i+8, j:j+8] = utils.idct2(dct_Y[i:i+8, j:j+8])

            ycrcb[:, :, 0] = np.clip(Y_rec + 128, 0, 255).astype(np.uint8)
            img_finale = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
            
            cv2.imwrite(output_path, img_finale)
            return True

    def decode(self, original_path, watermarked_path):
        img_o = cv2.imread(original_path)
        img_t = cv2.imread(watermarked_path)
        if img_o is None or img_t is None: return "Erreur: Fichiers manquants"

        host_o, h, w = self._prepare_dimensions(img_o)
        host_t, _, _ = self._prepare_dimensions(img_t)

        dct_orig = self._get_dct_matrix(host_o, h, w)
        dct_tatou = self._get_dct_matrix(host_t, h, w)

        extracted_reps = []
        for r in range(self.repetitions):
            pos = self.pos_groups[r % 3]
            bits_r = []
            for i in range(0, h, 8):
                for j in range(0, w, 8):
                    votes = [1 if dct_tatou[i+u, j+v] > dct_orig[i+u, j+v] else 0 
                             for u, v in [self.zz[p] for p in pos]]
                    bits_r.append(1 if sum(votes) >= len(votes)/2 else 0)
            extracted_reps.append(bits_r)

        final_bits = utils.majority_vote_bits(np.array(extracted_reps))
        header_bytes = utils.bits_to_bytes(final_bits[:16])
        len_payload = int.from_bytes(header_bytes, byteorder='big')

        if 0 < len_payload < 2000:
            start, end = 16, 16 + (len_payload * 8)
            try:
                data = utils.bits_to_bytes(final_bits[start:end])
                decoded_msg, _, _ = self.rs.decode(data)
                return decoded_msg.decode('utf-8')
            except:
                return "Erreur: Correction Reed-Solomon impossible"
        return "Erreur: Header corrompu"

    def _get_dct_matrix(self, host, h, w):
        Y, _, _ = utils.rgb2ycbcr(host)
        Y0 = Y - 128
        mat = np.zeros_like(Y0)
        for i in range(0, h, 8):
            for j in range(0, w, 8):
                mat[i:i+8, j:j+8] = utils.dct2(Y0[i:i+8, j:j+8])
        return mat