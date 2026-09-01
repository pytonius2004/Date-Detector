package org.example.expiringgoods;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.ComponentActivity;
import androidx.annotation.NonNull;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.ImageCapture;
import androidx.camera.core.ImageCaptureException;
import androidx.camera.core.Preview;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.camera.view.PreviewView;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.exifinterface.media.ExifInterface;

import com.google.common.util.concurrent.ListenableFuture;
import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.text.Text;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.TextRecognizer;
import com.google.mlkit.vision.text.latin.TextRecognizerOptions;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Камера для распознавания названия товара.
 *
 * 1. Пользователь делает снимок упаковки.
 * 2. ML Kit распознаёт слова.
 * 3. На снимке появляются рамки; касанием выбираются нужные слова.
 * 4. "Принять" возвращает выбранный текст в PythonActivity.
 */
public class TextRecognitionActivity extends ComponentActivity {

    private static final int CAMERA_PERMISSION_REQUEST = 6101;

    private PreviewView previewView;
    private FrameLayout root;
    private TextView instructionText;
    private Button captureButton;
    private Button retakeButton;
    private Button acceptButton;
    private LinearLayout reviewButtons;

    private ProcessCameraProvider cameraProvider;
    private ImageCapture imageCapture;
    private ExecutorService cameraExecutor;
    private TextRecognizer textRecognizer;
    private SelectableTextOverlay overlay;

    private File capturedFile;

    private int dp(float value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private GradientDrawable rounded(int color, float radiusDp) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(color);
        drawable.setCornerRadius(dp(radiusDp));
        return drawable;
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        root = new FrameLayout(this);
        root.setBackgroundColor(Color.BLACK);

        previewView = new PreviewView(this);
        previewView.setImplementationMode(PreviewView.ImplementationMode.COMPATIBLE);
        root.addView(previewView, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
        ));

        instructionText = new TextView(this);
        instructionText.setText("Сфотографируйте упаковку товара");
        instructionText.setTextColor(Color.WHITE);
        instructionText.setTextSize(18);
        instructionText.setGravity(Gravity.CENTER);
        instructionText.setPadding(dp(14), dp(12), dp(14), dp(12));
        instructionText.setBackground(rounded(Color.argb(210, 25, 27, 31), 18));

        FrameLayout.LayoutParams instructionParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.WRAP_CONTENT
        );
        instructionParams.gravity = Gravity.TOP;
        instructionParams.leftMargin = dp(14);
        instructionParams.rightMargin = dp(14);
        instructionParams.topMargin = dp(18);
        root.addView(instructionText, instructionParams);

        captureButton = makeButton("Сфотографировать", Color.rgb(131, 18, 30));
        FrameLayout.LayoutParams captureParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                dp(62)
        );
        captureParams.gravity = Gravity.BOTTOM;
        captureParams.leftMargin = dp(16);
        captureParams.rightMargin = dp(16);
        captureParams.bottomMargin = dp(18);
        root.addView(captureButton, captureParams);

        reviewButtons = new LinearLayout(this);
        reviewButtons.setOrientation(LinearLayout.HORIZONTAL);
        reviewButtons.setGravity(Gravity.CENTER);
        reviewButtons.setPadding(0, 0, 0, 0);
        reviewButtons.setVisibility(View.GONE);

        retakeButton = makeButton("Переснять", Color.rgb(52, 54, 61));
        acceptButton = makeButton("Принять", Color.rgb(131, 18, 30));

        LinearLayout.LayoutParams left = new LinearLayout.LayoutParams(0, dp(62), 1f);
        left.rightMargin = dp(6);
        LinearLayout.LayoutParams right = new LinearLayout.LayoutParams(0, dp(62), 1f);
        right.leftMargin = dp(6);
        reviewButtons.addView(retakeButton, left);
        reviewButtons.addView(acceptButton, right);

        FrameLayout.LayoutParams reviewParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                dp(62)
        );
        reviewParams.gravity = Gravity.BOTTOM;
        reviewParams.leftMargin = dp(16);
        reviewParams.rightMargin = dp(16);
        reviewParams.bottomMargin = dp(18);
        root.addView(reviewButtons, reviewParams);

        setContentView(root);

        cameraExecutor = Executors.newSingleThreadExecutor();
        textRecognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);

        captureButton.setOnClickListener(v -> captureAndRecognize());
        retakeButton.setOnClickListener(v -> restartCamera());
        acceptButton.setOnClickListener(v -> acceptSelection());

        root.setOnApplyWindowInsetsListener((view, insets) -> {
            int top = insets.getSystemWindowInsetTop();
            int bottom = insets.getSystemWindowInsetBottom();

            FrameLayout.LayoutParams ip = (FrameLayout.LayoutParams) instructionText.getLayoutParams();
            ip.topMargin = top + dp(14);
            instructionText.setLayoutParams(ip);

            FrameLayout.LayoutParams cp = (FrameLayout.LayoutParams) captureButton.getLayoutParams();
            cp.bottomMargin = bottom + dp(16);
            captureButton.setLayoutParams(cp);

            FrameLayout.LayoutParams rp = (FrameLayout.LayoutParams) reviewButtons.getLayoutParams();
            rp.bottomMargin = bottom + dp(16);
            reviewButtons.setLayoutParams(rp);
            return insets;
        });
        root.requestApplyInsets();

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED) {
            startCamera();
        } else {
            ActivityCompat.requestPermissions(
                    this,
                    new String[]{Manifest.permission.CAMERA},
                    CAMERA_PERMISSION_REQUEST
            );
        }
    }

    private Button makeButton(String text, int background) {
        Button button = new Button(this);
        button.setText(text);
        button.setTextSize(17);
        button.setTextColor(Color.WHITE);
        button.setAllCaps(false);
        button.setGravity(Gravity.CENTER);
        button.setBackground(rounded(background, 18));
        return button;
    }

    private void startCamera() {
        ListenableFuture<ProcessCameraProvider> future = ProcessCameraProvider.getInstance(this);
        future.addListener(() -> {
            try {
                cameraProvider = future.get();
                Preview preview = new Preview.Builder().build();
                preview.setSurfaceProvider(previewView.getSurfaceProvider());

                imageCapture = new ImageCapture.Builder()
                        .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                        .build();

                cameraProvider.unbindAll();
                cameraProvider.bindToLifecycle(
                        this,
                        CameraSelector.DEFAULT_BACK_CAMERA,
                        preview,
                        imageCapture
                );
            } catch (ExecutionException | InterruptedException e) {
                Toast.makeText(this, "Не удалось запустить камеру: " + e.getMessage(), Toast.LENGTH_LONG).show();
                finish();
            }
        }, ContextCompat.getMainExecutor(this));
    }

    private void captureAndRecognize() {
        if (imageCapture == null) {
            return;
        }

        captureButton.setEnabled(false);
        instructionText.setText("Распознаю текст…");

        capturedFile = new File(getCacheDir(), "ocr_" + System.currentTimeMillis() + ".jpg");
        ImageCapture.OutputFileOptions options = new ImageCapture.OutputFileOptions.Builder(capturedFile).build();

        imageCapture.takePicture(
                options,
                cameraExecutor,
                new ImageCapture.OnImageSavedCallback() {
                    @Override
                    public void onImageSaved(@NonNull ImageCapture.OutputFileResults outputFileResults) {
                        runOnUiThread(() -> processCapturedFile(capturedFile));
                    }

                    @Override
                    public void onError(@NonNull ImageCaptureException exception) {
                        runOnUiThread(() -> {
                            captureButton.setEnabled(true);
                            instructionText.setText("Не удалось сделать снимок. Попробуйте ещё раз");
                            Toast.makeText(TextRecognitionActivity.this,
                                    "Ошибка камеры: " + exception.getMessage(),
                                    Toast.LENGTH_LONG).show();
                        });
                    }
                }
        );
    }

    private void processCapturedFile(File file) {
        try {
            Bitmap bitmap = loadUprightBitmap(file);
            if (bitmap == null) {
                throw new IOException("Не удалось открыть фотографию");
            }

            InputImage image = InputImage.fromBitmap(bitmap, 0);
            textRecognizer.process(image)
                    .addOnSuccessListener(result -> showRecognizedText(bitmap, result))
                    .addOnFailureListener(error -> {
                        captureButton.setEnabled(true);
                        instructionText.setText("Текст не распознан. Попробуйте ещё раз");
                        Toast.makeText(this,
                                "Ошибка распознавания: " + error.getMessage(),
                                Toast.LENGTH_LONG).show();
                    });
        } catch (Exception error) {
            captureButton.setEnabled(true);
            instructionText.setText("Не удалось обработать фотографию");
            Toast.makeText(this, error.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private Bitmap loadUprightBitmap(File file) throws IOException {
        Bitmap source = BitmapFactory.decodeFile(file.getAbsolutePath());
        if (source == null) {
            return null;
        }

        ExifInterface exif = new ExifInterface(file.getAbsolutePath());
        int orientation = exif.getAttributeInt(
                ExifInterface.TAG_ORIENTATION,
                ExifInterface.ORIENTATION_NORMAL
        );
        int degrees = 0;
        if (orientation == ExifInterface.ORIENTATION_ROTATE_90) degrees = 90;
        else if (orientation == ExifInterface.ORIENTATION_ROTATE_180) degrees = 180;
        else if (orientation == ExifInterface.ORIENTATION_ROTATE_270) degrees = 270;

        if (degrees == 0) {
            return source;
        }

        Matrix matrix = new Matrix();
        matrix.postRotate(degrees);
        Bitmap rotated = Bitmap.createBitmap(
                source, 0, 0, source.getWidth(), source.getHeight(), matrix, true
        );
        if (rotated != source) {
            source.recycle();
        }
        return rotated;
    }

    private void showRecognizedText(Bitmap bitmap, Text result) {
        List<WordRegion> regions = new ArrayList<>();
        for (Text.TextBlock block : result.getTextBlocks()) {
            for (Text.Line line : block.getLines()) {
                for (Text.Element element : line.getElements()) {
                    Rect box = element.getBoundingBox();
                    String value = element.getText() == null ? "" : element.getText().trim();
                    if (box != null && !value.isEmpty()) {
                        regions.add(new WordRegion(new Rect(box), value));
                    }
                }
            }
        }

        if (regions.isEmpty()) {
            captureButton.setEnabled(true);
            instructionText.setText("Текст не найден. Попробуйте снять ближе");
            Toast.makeText(this, "На фотографии не удалось найти текст", Toast.LENGTH_LONG).show();
            return;
        }

        if (cameraProvider != null) {
            cameraProvider.unbindAll();
        }

        overlay = new SelectableTextOverlay(this, bitmap, regions);
        root.addView(overlay, 1, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
        ));

        instructionText.bringToFront();
        reviewButtons.bringToFront();
        captureButton.setVisibility(View.GONE);
        reviewButtons.setVisibility(View.VISIBLE);
        instructionText.setText("Нажмите на нужные слова на упаковке, затем «Принять»");
    }

    private void restartCamera() {
        if (overlay != null) {
            root.removeView(overlay);
            overlay.releaseBitmap();
            overlay = null;
        }
        reviewButtons.setVisibility(View.GONE);
        captureButton.setVisibility(View.VISIBLE);
        captureButton.setEnabled(true);
        instructionText.setText("Сфотографируйте упаковку товара");
        startCamera();
    }

    private void acceptSelection() {
        if (overlay == null) {
            return;
        }
        String selected = overlay.getSelectedText();
        if (selected.isEmpty()) {
            Toast.makeText(this, "Сначала выберите текст на упаковке", Toast.LENGTH_SHORT).show();
            return;
        }

        Intent result = new Intent();
        result.putExtra("recognized_text", selected);
        setResult(RESULT_OK, result);
        finish();
    }

    @Override
    public void onRequestPermissionsResult(
            int requestCode,
            @NonNull String[] permissions,
            @NonNull int[] grantResults
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == CAMERA_PERMISSION_REQUEST) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                startCamera();
            } else {
                Toast.makeText(this, "Разрешение камеры не предоставлено", Toast.LENGTH_LONG).show();
                finish();
            }
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (cameraProvider != null) {
            cameraProvider.unbindAll();
        }
        if (textRecognizer != null) {
            textRecognizer.close();
        }
        if (cameraExecutor != null) {
            cameraExecutor.shutdown();
        }
        if (overlay != null) {
            overlay.releaseBitmap();
        }
        if (capturedFile != null && capturedFile.exists()) {
            //noinspection ResultOfMethodCallIgnored
            capturedFile.delete();
        }
    }

    private static final class WordRegion {
        final Rect box;
        final String text;
        boolean selected;

        WordRegion(Rect box, String text) {
            this.box = box;
            this.text = text;
        }
    }

    /** Рисует фотографию и кликабельные рамки распознанных слов. */
    private static final class SelectableTextOverlay extends View {
        private Bitmap bitmap;
        private final List<WordRegion> regions;
        private final Paint imagePaint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
        private final Paint normalPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint selectedFillPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint selectedBorderPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF destination = new RectF();
        private float scale = 1f;
        private float offsetX = 0f;
        private float offsetY = 0f;

        SelectableTextOverlay(TextRecognitionActivity context, Bitmap bitmap, List<WordRegion> regions) {
            super(context);
            this.bitmap = bitmap;
            this.regions = regions;
            setBackgroundColor(Color.BLACK);

            normalPaint.setStyle(Paint.Style.STROKE);
            normalPaint.setStrokeWidth(context.dp(1.5f));
            normalPaint.setColor(Color.argb(215, 255, 255, 255));

            selectedFillPaint.setStyle(Paint.Style.FILL);
            selectedFillPaint.setColor(Color.argb(105, 255, 214, 10));

            selectedBorderPaint.setStyle(Paint.Style.STROKE);
            selectedBorderPaint.setStrokeWidth(context.dp(2.5f));
            selectedBorderPaint.setColor(Color.rgb(255, 214, 10));
        }

        @Override
        protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            if (bitmap == null) return;

            float sx = getWidth() / (float) bitmap.getWidth();
            float sy = getHeight() / (float) bitmap.getHeight();
            scale = Math.min(sx, sy);
            float drawW = bitmap.getWidth() * scale;
            float drawH = bitmap.getHeight() * scale;
            offsetX = (getWidth() - drawW) / 2f;
            offsetY = (getHeight() - drawH) / 2f;
            destination.set(offsetX, offsetY, offsetX + drawW, offsetY + drawH);

            canvas.drawBitmap(bitmap, null, destination, imagePaint);

            for (WordRegion region : regions) {
                RectF r = toView(region.box);
                if (region.selected) {
                    canvas.drawRoundRect(r, 5f, 5f, selectedFillPaint);
                    canvas.drawRoundRect(r, 5f, 5f, selectedBorderPaint);
                } else {
                    canvas.drawRoundRect(r, 5f, 5f, normalPaint);
                }
            }
        }

        private RectF toView(Rect box) {
            return new RectF(
                    offsetX + box.left * scale,
                    offsetY + box.top * scale,
                    offsetX + box.right * scale,
                    offsetY + box.bottom * scale
            );
        }

        @Override
        public boolean onTouchEvent(MotionEvent event) {
            if (event.getAction() != MotionEvent.ACTION_UP || bitmap == null) {
                return true;
            }

            float imageX = (event.getX() - offsetX) / scale;
            float imageY = (event.getY() - offsetY) / scale;

            WordRegion best = null;
            float bestArea = Float.MAX_VALUE;
            for (WordRegion region : regions) {
                Rect b = region.box;
                int extra = 12;
                if (imageX >= b.left - extra && imageX <= b.right + extra
                        && imageY >= b.top - extra && imageY <= b.bottom + extra) {
                    float area = Math.max(1, b.width() * b.height());
                    if (area < bestArea) {
                        best = region;
                        bestArea = area;
                    }
                }
            }

            if (best != null) {
                best.selected = !best.selected;
                invalidate();
            }
            return true;
        }

        String getSelectedText() {
            List<WordRegion> selected = new ArrayList<>();
            for (WordRegion region : regions) {
                if (region.selected) selected.add(region);
            }
            selected.sort(Comparator
                    .comparingInt((WordRegion r) -> r.box.top)
                    .thenComparingInt(r -> r.box.left));

            StringBuilder builder = new StringBuilder();
            for (WordRegion region : selected) {
                if (builder.length() > 0) builder.append(' ');
                builder.append(region.text);
            }
            return builder.toString().trim();
        }

        void releaseBitmap() {
            if (bitmap != null && !bitmap.isRecycled()) {
                bitmap.recycle();
            }
            bitmap = null;
        }
    }
}

import com.google.common.util.concurrent.ListenableFuture;
import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.text.Text;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.TextRecognizer;
import com.google.mlkit.vision.text.latin.TextRecognizerOptions;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Камера для распознавания названия товара.
 *
 * 1. Пользователь делает снимок упаковки.
 * 2. ML Kit распознаёт слова.
 * 3. На снимке появляются рамки; касанием выбираются нужные слова.
 * 4. "Принять" возвращает выбранный текст в PythonActivity.
 */
public class TextRecognitionActivity extends ComponentActivity {

    private static final int CAMERA_PERMISSION_REQUEST = 6101;

    private PreviewView previewView;
    private FrameLayout root;
    private TextView instructionText;
    private Button captureButton;
    private Button retakeButton;
    private Button acceptButton;
    private LinearLayout reviewButtons;

    private ProcessCameraProvider cameraProvider;
    private ImageCapture imageCapture;
    private ExecutorService cameraExecutor;
    private TextRecognizer textRecognizer;
    private SelectableTextOverlay overlay;

    private File capturedFile;

    private int dp(float value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private GradientDrawable rounded(int color, float radiusDp) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(color);
        drawable.setCornerRadius(dp(radiusDp));
        return drawable;
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        root = new FrameLayout(this);
        root.setBackgroundColor(Color.BLACK);

        previewView = new PreviewView(this);
        previewView.setImplementationMode(PreviewView.ImplementationMode.COMPATIBLE);
        root.addView(previewView, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
        ));

        instructionText = new TextView(this);
        instructionText.setText("Сфотографируйте упаковку товара");
        instructionText.setTextColor(Color.WHITE);
        instructionText.setTextSize(18);
        instructionText.setGravity(Gravity.CENTER);
        instructionText.setPadding(dp(14), dp(12), dp(14), dp(12));
        instructionText.setBackground(rounded(Color.argb(210, 25, 27, 31), 18));

        FrameLayout.LayoutParams instructionParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.WRAP_CONTENT
        );
        instructionParams.gravity = Gravity.TOP;
        instructionParams.leftMargin = dp(14);
        instructionParams.rightMargin = dp(14);
        instructionParams.topMargin = dp(18);
        root.addView(instructionText, instructionParams);

        captureButton = makeButton("Сфотографировать", Color.rgb(131, 18, 30));
        FrameLayout.LayoutParams captureParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                dp(62)
        );
        captureParams.gravity = Gravity.BOTTOM;
        captureParams.leftMargin = dp(16);
        captureParams.rightMargin = dp(16);
        captureParams.bottomMargin = dp(18);
        root.addView(captureButton, captureParams);

        reviewButtons = new LinearLayout(this);
        reviewButtons.setOrientation(LinearLayout.HORIZONTAL);
        reviewButtons.setGravity(Gravity.CENTER);
        reviewButtons.setPadding(0, 0, 0, 0);
        reviewButtons.setVisibility(View.GONE);

        retakeButton = makeButton("Переснять", Color.rgb(52, 54, 61));
        acceptButton = makeButton("Принять", Color.rgb(131, 18, 30));

        LinearLayout.LayoutParams left = new LinearLayout.LayoutParams(0, dp(62), 1f);
        left.rightMargin = dp(6);
        LinearLayout.LayoutParams right = new LinearLayout.LayoutParams(0, dp(62), 1f);
        right.leftMargin = dp(6);
        reviewButtons.addView(retakeButton, left);
        reviewButtons.addView(acceptButton, right);

        FrameLayout.LayoutParams reviewParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                dp(62)
        );
        reviewParams.gravity = Gravity.BOTTOM;
        reviewParams.leftMargin = dp(16);
        reviewParams.rightMargin = dp(16);
        reviewParams.bottomMargin = dp(18);
        root.addView(reviewButtons, reviewParams);

        setContentView(root);

        cameraExecutor = Executors.newSingleThreadExecutor();
        textRecognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);

        captureButton.setOnClickListener(v -> captureAndRecognize());
        retakeButton.setOnClickListener(v -> restartCamera());
        acceptButton.setOnClickListener(v -> acceptSelection());

        root.setOnApplyWindowInsetsListener((view, insets) -> {
            int top = insets.getSystemWindowInsetTop();
            int bottom = insets.getSystemWindowInsetBottom();

            FrameLayout.LayoutParams ip = (FrameLayout.LayoutParams) instructionText.getLayoutParams();
            ip.topMargin = top + dp(14);
            instructionText.setLayoutParams(ip);

            FrameLayout.LayoutParams cp = (FrameLayout.LayoutParams) captureButton.getLayoutParams();
            cp.bottomMargin = bottom + dp(16);
            captureButton.setLayoutParams(cp);

            FrameLayout.LayoutParams rp = (FrameLayout.LayoutParams) reviewButtons.getLayoutParams();
            rp.bottomMargin = bottom + dp(16);
            reviewButtons.setLayoutParams(rp);
            return insets;
        });
        root.requestApplyInsets();

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED) {
            startCamera();
        } else {
            ActivityCompat.requestPermissions(
                    this,
                    new String[]{Manifest.permission.CAMERA},
                    CAMERA_PERMISSION_REQUEST
            );
        }
    }

    private Button makeButton(String text, int background) {
        Button button = new Button(this);
        button.setText(text);
        button.setTextSize(17);
        button.setTextColor(Color.WHITE);
        button.setAllCaps(false);
        button.setGravity(Gravity.CENTER);
        button.setBackground(rounded(background, 18));
        return button;
    }

    private void startCamera() {
        ListenableFuture<ProcessCameraProvider> future = ProcessCameraProvider.getInstance(this);
        future.addListener(() -> {
            try {
                cameraProvider = future.get();
                Preview preview = new Preview.Builder().build();
                preview.setSurfaceProvider(previewView.getSurfaceProvider());

                imageCapture = new ImageCapture.Builder()
                        .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                        .build();

                cameraProvider.unbindAll();
                cameraProvider.bindToLifecycle(
                        this,
                        CameraSelector.DEFAULT_BACK_CAMERA,
                        preview,
                        imageCapture
                );
            } catch (ExecutionException | InterruptedException e) {
                Toast.makeText(this, "Не удалось запустить камеру: " + e.getMessage(), Toast.LENGTH_LONG).show();
                finish();
            }
        }, ContextCompat.getMainExecutor(this));
    }

    private void captureAndRecognize() {
        if (imageCapture == null) {
            return;
        }

        captureButton.setEnabled(false);
        instructionText.setText("Распознаю текст…");

        capturedFile = new File(getCacheDir(), "ocr_" + System.currentTimeMillis() + ".jpg");
        ImageCapture.OutputFileOptions options = new ImageCapture.OutputFileOptions.Builder(capturedFile).build();

        imageCapture.takePicture(
                options,
                cameraExecutor,
                new ImageCapture.OnImageSavedCallback() {
                    @Override
                    public void onImageSaved(@NonNull ImageCapture.OutputFileResults outputFileResults) {
                        runOnUiThread(() -> processCapturedFile(capturedFile));
                    }

                    @Override
                    public void onError(@NonNull ImageCaptureException exception) {
                        runOnUiThread(() -> {
                            captureButton.setEnabled(true);
                            instructionText.setText("Не удалось сделать снимок. Попробуйте ещё раз");
                            Toast.makeText(TextRecognitionActivity.this,
                                    "Ошибка камеры: " + exception.getMessage(),
                                    Toast.LENGTH_LONG).show();
                        });
                    }
                }
        );
    }

    private void processCapturedFile(File file) {
        try {
            Bitmap bitmap = loadUprightBitmap(file);
            if (bitmap == null) {
                throw new IOException("Не удалось открыть фотографию");
            }

            InputImage image = InputImage.fromBitmap(bitmap, 0);
            textRecognizer.process(image)
                    .addOnSuccessListener(result -> showRecognizedText(bitmap, result))
                    .addOnFailureListener(error -> {
                        captureButton.setEnabled(true);
                        instructionText.setText("Текст не распознан. Попробуйте ещё раз");
                        Toast.makeText(this,
                                "Ошибка распознавания: " + error.getMessage(),
                                Toast.LENGTH_LONG).show();
                    });
        } catch (Exception error) {
            captureButton.setEnabled(true);
            instructionText.setText("Не удалось обработать фотографию");
            Toast.makeText(this, error.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private Bitmap loadUprightBitmap(File file) throws IOException {
        Bitmap source = BitmapFactory.decodeFile(file.getAbsolutePath());
        if (source == null) {
            return null;
        }

        ExifInterface exif = new ExifInterface(file.getAbsolutePath());
        int orientation = exif.getAttributeInt(
                ExifInterface.TAG_ORIENTATION,
                ExifInterface.ORIENTATION_NORMAL
        );
        int degrees = 0;
        if (orientation == ExifInterface.ORIENTATION_ROTATE_90) degrees = 90;
        else if (orientation == ExifInterface.ORIENTATION_ROTATE_180) degrees = 180;
        else if (orientation == ExifInterface.ORIENTATION_ROTATE_270) degrees = 270;

        if (degrees == 0) {
            return source;
        }

        Matrix matrix = new Matrix();
        matrix.postRotate(degrees);
        Bitmap rotated = Bitmap.createBitmap(
                source, 0, 0, source.getWidth(), source.getHeight(), matrix, true
        );
        if (rotated != source) {
            source.recycle();
        }
        return rotated;
    }

    private void showRecognizedText(Bitmap bitmap, Text result) {
        List<WordRegion> regions = new ArrayList<>();
        for (Text.TextBlock block : result.getTextBlocks()) {
            for (Text.Line line : block.getLines()) {
                for (Text.Element element : line.getElements()) {
                    Rect box = element.getBoundingBox();
                    String value = element.getText() == null ? "" : element.getText().trim();
                    if (box != null && !value.isEmpty()) {
                        regions.add(new WordRegion(new Rect(box), value));
                    }
                }
            }
        }

        if (regions.isEmpty()) {
            captureButton.setEnabled(true);
            instructionText.setText("Текст не найден. Попробуйте снять ближе");
            Toast.makeText(this, "На фотографии не удалось найти текст", Toast.LENGTH_LONG).show();
            return;
        }

        if (cameraProvider != null) {
            cameraProvider.unbindAll();
        }

        overlay = new SelectableTextOverlay(this, bitmap, regions);
        root.addView(overlay, 1, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
        ));

        instructionText.bringToFront();
        reviewButtons.bringToFront();
        captureButton.setVisibility(View.GONE);
        reviewButtons.setVisibility(View.VISIBLE);
        instructionText.setText("Нажмите на нужные слова на упаковке, затем «Принять»");
    }

    private void restartCamera() {
        if (overlay != null) {
            root.removeView(overlay);
            overlay.releaseBitmap();
            overlay = null;
        }
        reviewButtons.setVisibility(View.GONE);
        captureButton.setVisibility(View.VISIBLE);
        captureButton.setEnabled(true);
        instructionText.setText("Сфотографируйте упаковку товара");
        startCamera();
    }

    private void acceptSelection() {
        if (overlay == null) {
            return;
        }
        String selected = overlay.getSelectedText();
        if (selected.isEmpty()) {
            Toast.makeText(this, "Сначала выберите текст на упаковке", Toast.LENGTH_SHORT).show();
            return;
        }

        Intent result = new Intent();
        result.putExtra("recognized_text", selected);
        setResult(RESULT_OK, result);
        finish();
    }

    @Override
    public void onRequestPermissionsResult(
            int requestCode,
            @NonNull String[] permissions,
            @NonNull int[] grantResults
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == CAMERA_PERMISSION_REQUEST) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                startCamera();
            } else {
                Toast.makeText(this, "Разрешение камеры не предоставлено", Toast.LENGTH_LONG).show();
                finish();
            }
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (cameraProvider != null) {
            cameraProvider.unbindAll();
        }
        if (textRecognizer != null) {
            textRecognizer.close();
        }
        if (cameraExecutor != null) {
            cameraExecutor.shutdown();
        }
        if (overlay != null) {
            overlay.releaseBitmap();
        }
        if (capturedFile != null && capturedFile.exists()) {
            //noinspection ResultOfMethodCallIgnored
            capturedFile.delete();
        }
    }

    private static final class WordRegion {
        final Rect box;
        final String text;
        boolean selected;

        WordRegion(Rect box, String text) {
            this.box = box;
            this.text = text;
        }
    }

    /** Рисует фотографию и кликабельные рамки распознанных слов. */
    private static final class SelectableTextOverlay extends View {
        private Bitmap bitmap;
        private final List<WordRegion> regions;
        private final Paint imagePaint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
        private final Paint normalPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint selectedFillPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint selectedBorderPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF destination = new RectF();
        private float scale = 1f;
        private float offsetX = 0f;
        private float offsetY = 0f;

        SelectableTextOverlay(TextRecognitionActivity context, Bitmap bitmap, List<WordRegion> regions) {
            super(context);
            this.bitmap = bitmap;
            this.regions = regions;
            setBackgroundColor(Color.BLACK);

            normalPaint.setStyle(Paint.Style.STROKE);
            normalPaint.setStrokeWidth(context.dp(1.5f));
            normalPaint.setColor(Color.argb(215, 255, 255, 255));

            selectedFillPaint.setStyle(Paint.Style.FILL);
            selectedFillPaint.setColor(Color.argb(105, 255, 214, 10));

            selectedBorderPaint.setStyle(Paint.Style.STROKE);
            selectedBorderPaint.setStrokeWidth(context.dp(2.5f));
            selectedBorderPaint.setColor(Color.rgb(255, 214, 10));
        }

        @Override
        protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            if (bitmap == null) return;

            float sx = getWidth() / (float) bitmap.getWidth();
            float sy = getHeight() / (float) bitmap.getHeight();
            scale = Math.min(sx, sy);
            float drawW = bitmap.getWidth() * scale;
            float drawH = bitmap.getHeight() * scale;
            offsetX = (getWidth() - drawW) / 2f;
            offsetY = (getHeight() - drawH) / 2f;
            destination.set(offsetX, offsetY, offsetX + drawW, offsetY + drawH);

            canvas.drawBitmap(bitmap, null, destination, imagePaint);

            for (WordRegion region : regions) {
                RectF r = toView(region.box);
                if (region.selected) {
                    canvas.drawRoundRect(r, 5f, 5f, selectedFillPaint);
                    canvas.drawRoundRect(r, 5f, 5f, selectedBorderPaint);
                } else {
                    canvas.drawRoundRect(r, 5f, 5f, normalPaint);
                }
            }
        }

        private RectF toView(Rect box) {
            return new RectF(
                    offsetX + box.left * scale,
                    offsetY + box.top * scale,
                    offsetX + box.right * scale,
                    offsetY + box.bottom * scale
            );
        }

        @Override
        public boolean onTouchEvent(MotionEvent event) {
            if (event.getAction() != MotionEvent.ACTION_UP || bitmap == null) {
                return true;
            }

            float imageX = (event.getX() - offsetX) / scale;
            float imageY = (event.getY() - offsetY) / scale;

            WordRegion best = null;
            float bestArea = Float.MAX_VALUE;
            for (WordRegion region : regions) {
                Rect b = region.box;
                int extra = 12;
                if (imageX >= b.left - extra && imageX <= b.right + extra
                        && imageY >= b.top - extra && imageY <= b.bottom + extra) {
                    float area = Math.max(1, b.width() * b.height());
                    if (area < bestArea) {
                        best = region;
                        bestArea = area;
                    }
                }
            }

            if (best != null) {
                best.selected = !best.selected;
                invalidate();
            }
            return true;
        }

        String getSelectedText() {
            List<WordRegion> selected = new ArrayList<>();
            for (WordRegion region : regions) {
                if (region.selected) selected.add(region);
            }
            selected.sort(Comparator
                    .comparingInt((WordRegion r) -> r.box.top)
                    .thenComparingInt(r -> r.box.left));

            StringBuilder builder = new StringBuilder();
            for (WordRegion region : selected) {
                if (builder.length() > 0) builder.append(' ');
                builder.append(region.text);
            }
            return builder.toString().trim();
        }

        void releaseBitmap() {
            if (bitmap != null && !bitmap.isRecycled()) {
                bitmap.recycle();
            }
            bitmap = null;
        }
    }
}
