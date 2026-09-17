"""
BrailleVision - Command-line Inference Script
Run: python inference_cli.py --image path/to/braille.jpg --output result.jpg
"""

import argparse
import cv2
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from inference import run_inference, draw_results
from braille_decoder import decode_sequence


def main():
    parser = argparse.ArgumentParser(
        description='BrailleVision - Braille Detection CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python inference_cli.py --image braille.jpg
  python inference_cli.py --image braille.jpg --output result.jpg
  python inference_cli.py --image braille.jpg --json
  python inference_cli.py --webcam
        """
    )
    parser.add_argument('--image', '-i', type=str, help='Path to input image')
    parser.add_argument('--output', '-o', type=str, help='Path to save annotated output image')
    parser.add_argument('--json', '-j', action='store_true', help='Output results as JSON')
    parser.add_argument('--webcam', '-w', action='store_true', help='Use webcam for live detection')
    parser.add_argument('--model', '-m', type=str, default='models/best.pt', help='Path to YOLO model weights')

    args = parser.parse_args()

    if args.webcam:
        run_webcam_mode()
        return

    if not args.image:
        parser.print_help()
        sys.exit(1)

    img_path = Path(args.image)
    if not img_path.exists():
        print(f"❌ Image not found: {img_path}")
        sys.exit(1)

    image = cv2.imread(str(img_path))
    if image is None:
        print(f"❌ Could not read image: {img_path}")
        sys.exit(1)

    print(f"📷 Processing: {img_path}")
    result = run_inference(image)

    if args.json:
        # Remove large data for CLI output
        output_result = {k: v for k, v in result.items() if k != 'cells_data'}
        print(json.dumps(output_result, indent=2))
    else:
        print(f"\n{'='*50}")
        print(f"  BrailleVision Results")
        print(f"{'='*50}")
        print(f"  📝 Decoded Text  : {result['text'] or '(nothing detected)'}")
        print(f"  🎯 Confidence    : {result['confidence']*100:.1f}%")
        print(f"  🔵 Cells Found   : {result['cells_detected']}")
        print(f"  ⚡ Method        : {result['method']}")
        print(f"{'='*50}\n")

    if args.output:
        annotated = draw_results(image, result)
        cv2.imwrite(args.output, annotated)
        print(f"💾 Saved annotated image to: {args.output}")
    elif not args.json:
        # Show in window
        annotated = draw_results(image, result)
        cv2.imshow('BrailleVision - Detection Result', annotated)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


def run_webcam_mode():
    """Live webcam Braille detection."""
    print("🎥 Starting webcam mode... Press 'q' to quit, 's' to save frame")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open webcam")
        sys.exit(1)

    frame_count = 0
    process_every = 5  # process every 5th frame for performance

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        display = frame.copy()

        if frame_count % process_every == 0:
            result = run_inference(frame)
            display = draw_results(frame, result)

            # Show FPS and stats
            text = result.get('text', '')
            if text:
                print(f"\r📝 Detected: {text:<30} | Conf: {result['confidence']*100:.0f}%", end='', flush=True)

        # Show frame
        cv2.imshow('BrailleVision - Live Detection (press q to quit)', display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            save_path = f"capture_{frame_count}.jpg"
            cv2.imwrite(save_path, frame)
            print(f"\n💾 Saved: {save_path}")

    cap.release()
    cv2.destroyAllWindows()
    print("\n👋 Webcam closed")


if __name__ == '__main__':
    main()
