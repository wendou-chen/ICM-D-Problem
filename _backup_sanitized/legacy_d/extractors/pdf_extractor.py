import logging
import pandas as pd
import os
import re
from src.extractors.base_extractors import BaseExtractor
from src.utils.common import RequestUtils

logger = logging.getLogger("WNBAPipeline")

class TVBDMAExtractor(BaseExtractor):
    """
    Extracts DMA data from TVB PDF.
    Requires: pip install pdfplumber
    """

    def extract(self, season: int = None) -> pd.DataFrame:
        url = self.config['external']['tvb_dma_pdf']
        local_path = f"{self.raw_dir}/tvb_dma.pdf"

        if not os.path.exists(local_path):
            logger.info(f"Downloading PDF from {url}")
            RequestUtils.download_file(url, local_path)

        try:
            import pdfplumber

            data = []
            with pdfplumber.open(local_path) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if table:
                        # Logic to parse the specific TVB layout
                        # Usually: Rank, DMA Name, TV Homes, % of US
                        # We need to find rows with WNBA teams or map DMA to cities
                        headers = table[0]
                        for row in table[1:]:
                            if len(row) > 2:
                                data.append({
                                    "dma_rank": row[0],
                                    "dma_name": row[1],
                                    "tv_homes": row[2] if len(row) > 2 else None
                                })

            df = pd.DataFrame(data)
            # Basic cleaning
            df['dma_rank'] = pd.to_numeric(df['dma_rank'], errors='coerce')
            df = df.dropna(subset=['dma_rank'])
            df['source'] = 'tvb_pdf'
            return df

        except ImportError:
            logger.error("pdfplumber not installed. Cannot parse PDF.")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"PDF parsing error: {e}")
            return pd.DataFrame()
