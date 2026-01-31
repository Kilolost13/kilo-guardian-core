import api from './api';

export interface CapturedImage {
  deviceId: string;
  label: string;
  dataUrl: string;
  timestamp: number;
}

export interface OCRResult {
  index: number;
  filename: string;
  text: string;
  confidence?: number;
  char_count?: number;
  success: boolean;
  error?: string;
}

export interface BatchOCRResponse {
  success: boolean;
  total_images: number;
  successful_ocr: number;
  failed_ocr: number;
  individual_results: OCRResult[];
  combined_text: string;
  common_words: string[];
  recommended_result_index: number;
}

/**
 * Convert data URL to File object
 */
const dataURLtoFile = (dataUrl: string, filename: string): File => {
  const arr = dataUrl.split(',');
  const mime = arr[0].match(/:(.*?);/)?.[1] || 'image/jpeg';
  const bstr = atob(arr[1]);
  let n = bstr.length;
  const u8arr = new Uint8Array(n);
  while (n--) {
    u8arr[n] = bstr.charCodeAt(n);
  }
  return new File([u8arr], filename, { type: mime });
};

/**
 * Send multiple images to batch OCR endpoint
 */
export const processBatchOCR = async (
  images: CapturedImage[]
): Promise<BatchOCRResponse> => {
  if (images.length === 0) {
    throw new Error('No images provided');
  }

  if (images.length > 10) {
    throw new Error('Maximum 10 images allowed');
  }

  // Convert data URLs to File objects
  const formData = new FormData();
  images.forEach((image, index) => {
    const file = dataURLtoFile(
      image.dataUrl,
      `camera-${image.deviceId}-${index}.jpg`
    );
    formData.append('files', file);
  });

  // Send to camera service batch OCR endpoint
  const response = await api.post<BatchOCRResponse>(
    '/cam/ocr/batch',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 60000, // 60 second timeout for batch processing
    }
  );

  return response.data;
};

/**
 * Process single image for OCR (fallback)
 */
export const processSingleOCR = async (
  image: CapturedImage
): Promise<{ text: string }> => {
  const file = dataURLtoFile(
    image.dataUrl,
    `camera-${image.deviceId}.jpg`
  );

  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post<{ text: string }>(
    '/cam/ocr',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );

  return response.data;
};

/**
 * Send multi-angle images for prescription analysis
 */
export const analyzePrescriptionMultiAngle = async (
  images: CapturedImage[]
): Promise<any> => {
  // First, get OCR from all angles
  const ocrResult = await processBatchOCR(images);

  // Send the combined text to AI Brain for prescription analysis
  const formData = new FormData();

  // Use the best image (highest confidence/char count)
  const bestImage = images[ocrResult.recommended_result_index] || images[0];
  const file = dataURLtoFile(
    bestImage.dataUrl,
    `prescription-${Date.now()}.jpg`
  );
  formData.append('image', file);

  const response = await api.post(
    '/ai_brain/analyze/prescription',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );

  return {
    ...response.data,
    ocr_results: ocrResult,
    images_processed: images.length,
  };
};

/**
 * Send multi-angle images for receipt/budget analysis
 */
export const analyzeReceiptMultiAngle = async (
  images: CapturedImage[]
): Promise<any> => {
  const ocrResult = await processBatchOCR(images);

  // Send combined text to AI Brain for financial analysis
  const response = await api.post(
    '/ai_brain/analyze/receipt',
    {
      text: ocrResult.combined_text,
      multi_angle_data: {
        images_count: images.length,
        confidence: ocrResult.individual_results.map(r => r.confidence),
        all_texts: ocrResult.individual_results.map(r => r.text),
      }
    }
  );

  return {
    ...response.data,
    ocr_results: ocrResult,
    images_processed: images.length,
  };
};
