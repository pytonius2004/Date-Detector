package org.example.expiringgoods;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.WindowInsets;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.ComponentActivity;
import androidx.annotation.NonNull;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.ImageAnalysis;
import androidx.camera.core.ImageProxy;
import androidx.camera.core.Preview;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.camera.view.PreviewView;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.google.common.util.concurrent.ListenableFuture;

import com.google.mlkit.vision.barcode.BarcodeScanner;
import com.google.mlkit.vision.barcode.BarcodeScannerOptions;
import com.google.mlkit.vision.barcode.BarcodeScanning;
import com.google.mlkit.vision.barcode.common.Barcode;
import com.google.mlkit.vision.common.InputImage;

import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;


/**
 * Нативный экран сканирования штрихкода.
 *
 * CameraX:
 *      камера
 *
 * Google ML Kit:
 *      распознавание штрихкода
 *
 * Возвращает PythonActivity:
 *
 * barcode = "..."
 *
 * или
 *
 * manual = true
 */
public class BarcodeScannerActivity
        extends ComponentActivity {

    private static final int CAMERA_PERMISSION_REQUEST =
            6001;

    private PreviewView previewView;

    private TextView instructionText;

    private Button manualButton;

    private ExecutorService cameraExecutor;

    private BarcodeScanner barcodeScanner;

    private final AtomicBoolean resultSent =
            new AtomicBoolean(false);


    // =====================================================
    // DP
    // =====================================================

    private int dp(float value) {

        return Math.round(
                value
                        *
                        getResources()
                                .getDisplayMetrics()
                                .density
        );
    }


    // =====================================================
    // ROUNDED BACKGROUND
    // =====================================================

    private GradientDrawable createRoundedBackground(
            int color,
            float radiusDp
    ) {

        GradientDrawable drawable =
                new GradientDrawable();

        drawable.setColor(
                color
        );

        drawable.setCornerRadius(
                dp(radiusDp)
        );

        return drawable;
    }


    // =====================================================
    // ON CREATE
    // =====================================================

    @Override
    protected void onCreate(
            Bundle savedInstanceState
    ) {

        super.onCreate(
                savedInstanceState
        );


        // -------------------------------------------------
        // ROOT
        // -------------------------------------------------

        FrameLayout root =
                new FrameLayout(this);


        // -------------------------------------------------
        // CAMERA PREVIEW
        // -------------------------------------------------

        previewView =
                new PreviewView(this);

        previewView.setImplementationMode(
                PreviewView
                        .ImplementationMode
                        .COMPATIBLE
        );

        FrameLayout.LayoutParams previewParams =
                new FrameLayout.LayoutParams(
                        FrameLayout.LayoutParams.MATCH_PARENT,
                        FrameLayout.LayoutParams.MATCH_PARENT
                );

        root.addView(
                previewView,
                previewParams
        );


        // -------------------------------------------------
        // TOP INSTRUCTION
        // -------------------------------------------------

        instructionText =
                new TextView(this);

        instructionText.setText(
                "Наведите камеру на штрихкод"
        );

        instructionText.setTextColor(
                Color.WHITE
        );

        instructionText.setTextSize(
                20
        );

        instructionText.setGravity(
                Gravity.CENTER
        );

        instructionText.setPadding(
                dp(16),
                dp(14),
                dp(16),
                dp(14)
        );

        instructionText.setBackground(
                createRoundedBackground(
                        Color.argb(
                                205,
                                25,
                                27,
                                31
                        ),
                        18
                )
        );

        instructionText.setElevation(
                dp(4)
        );


        FrameLayout.LayoutParams instructionParams =
                new FrameLayout.LayoutParams(
                        FrameLayout.LayoutParams.MATCH_PARENT,
                        FrameLayout.LayoutParams.WRAP_CONTENT
                );

        instructionParams.gravity =
                Gravity.TOP;

        instructionParams.leftMargin =
                dp(14);

        instructionParams.rightMargin =
                dp(14);

        root.addView(
                instructionText,
                instructionParams
        );


        // -------------------------------------------------
        // MANUAL BUTTON
        // -------------------------------------------------

        manualButton =
                new Button(this);

        manualButton.setText(
                "Добавить вручную"
        );

        manualButton.setTextSize(
                18
        );

        manualButton.setTextColor(
                Color.WHITE
        );

        manualButton.setAllCaps(
                false
        );

        manualButton.setGravity(
                Gravity.CENTER
        );

        manualButton.setPadding(
                dp(14),
                dp(8),
                dp(14),
                dp(8)
        );

        manualButton.setBackground(
                createRoundedBackground(
                        Color.rgb(
                                131,
                                18,
                                30
                        ),
                        18
                )
        );

        manualButton.setElevation(
                dp(5)
        );


        FrameLayout.LayoutParams manualParams =
                new FrameLayout.LayoutParams(
                        FrameLayout.LayoutParams.MATCH_PARENT,
                        dp(64)
                );

        manualParams.gravity =
                Gravity.BOTTOM;

        manualParams.leftMargin =
                dp(16);

        manualParams.rightMargin =
                dp(16);

        root.addView(
                manualButton,
                manualParams
        );


        manualButton.setOnClickListener(
                view -> returnManual()
        );


        // -------------------------------------------------
        // SAFE SYSTEM INSETS
        // -------------------------------------------------

        root.setOnApplyWindowInsetsListener(
                (view, insets) -> {

                    int topInset =
                            insets.getSystemWindowInsetTop();

                    int bottomInset =
                            insets.getSystemWindowInsetBottom();


                    // -------------------------------------
                    // TOP
                    // -------------------------------------

                    FrameLayout.LayoutParams topParams =
                            (FrameLayout.LayoutParams)
                                    instructionText
                                            .getLayoutParams();

                    topParams.topMargin =
                            topInset
                                    +
                                    dp(14);

                    topParams.leftMargin =
                            dp(14);

                    topParams.rightMargin =
                            dp(14);

                    instructionText.setLayoutParams(
                            topParams
                    );


                    // -------------------------------------
                    // BOTTOM
                    // -------------------------------------

                    FrameLayout.LayoutParams bottomParams =
                            (FrameLayout.LayoutParams)
                                    manualButton
                                            .getLayoutParams();

                    bottomParams.bottomMargin =
                            bottomInset
                                    +
                                    dp(16);

                    bottomParams.leftMargin =
                            dp(16);

                    bottomParams.rightMargin =
                            dp(16);

                    manualButton.setLayoutParams(
                            bottomParams
                    );


                    return insets;
                }
        );


        setContentView(
                root
        );


        root.requestApplyInsets();


        // -------------------------------------------------
        // CAMERA THREAD
        // -------------------------------------------------

        cameraExecutor =
                Executors.newSingleThreadExecutor();


        // -------------------------------------------------
        // ML KIT CONFIG
        // -------------------------------------------------

        BarcodeScannerOptions options =
                new BarcodeScannerOptions
                        .Builder()
                        .setBarcodeFormats(
                                Barcode.FORMAT_EAN_13,
                                Barcode.FORMAT_EAN_8,
                                Barcode.FORMAT_UPC_A,
                                Barcode.FORMAT_UPC_E,
                                Barcode.FORMAT_CODE_128,
                                Barcode.FORMAT_CODE_39,
                                Barcode.FORMAT_ITF
                        )
                        .build();


        barcodeScanner =
                BarcodeScanning.getClient(
                        options
                );


        // -------------------------------------------------
        // CAMERA PERMISSION
        // -------------------------------------------------

        if (
                ContextCompat.checkSelfPermission(
                        this,
                        Manifest.permission.CAMERA
                )
                        ==
                        PackageManager.PERMISSION_GRANTED
        ) {

            startCamera();

        } else {

            ActivityCompat.requestPermissions(
                    this,
                    new String[]{
                            Manifest.permission.CAMERA
                    },
                    CAMERA_PERMISSION_REQUEST
            );
        }
    }


    // =====================================================
    // CAMERA PERMISSION RESULT
    // =====================================================

    @Override
    public void onRequestPermissionsResult(
            int requestCode,
            @NonNull String[] permissions,
            @NonNull int[] grantResults
    ) {

        super.onRequestPermissionsResult(
                requestCode,
                permissions,
                grantResults
        );

        if (
                requestCode
                        ==
                        CAMERA_PERMISSION_REQUEST
        ) {

            if (
                    grantResults.length > 0
                            &&
                            grantResults[0]
                                    ==
                                    PackageManager.PERMISSION_GRANTED
            ) {

                startCamera();

            } else {

                Toast.makeText(
                        this,
                        "Разрешение камеры не предоставлено",
                        Toast.LENGTH_LONG
                ).show();

                finish();
            }
        }
    }


    // =====================================================
    // CAMERA
    // =====================================================

    private void startCamera() {

        ListenableFuture<ProcessCameraProvider>
                cameraProviderFuture =

                ProcessCameraProvider.getInstance(
                        this
                );


        cameraProviderFuture.addListener(
                () -> {

                    try {

                        ProcessCameraProvider
                                cameraProvider =
                                cameraProviderFuture.get();


                        // ---------------------------------
                        // PREVIEW
                        // ---------------------------------

                        Preview preview =
                                new Preview
                                        .Builder()
                                        .build();

                        preview.setSurfaceProvider(
                                previewView
                                        .getSurfaceProvider()
                        );


                        // ---------------------------------
                        // IMAGE ANALYSIS
                        // ---------------------------------

                        ImageAnalysis imageAnalysis =
                                new ImageAnalysis
                                        .Builder()
                                        .setBackpressureStrategy(
                                                ImageAnalysis
                                                        .STRATEGY_KEEP_ONLY_LATEST
                                        )
                                        .build();


                        imageAnalysis.setAnalyzer(
                                cameraExecutor,
                                this::analyzeFrame
                        );


                        // ---------------------------------
                        // BACK CAMERA
                        // ---------------------------------

                        CameraSelector cameraSelector =
                                CameraSelector
                                        .DEFAULT_BACK_CAMERA;


                        cameraProvider.unbindAll();


                        cameraProvider.bindToLifecycle(
                                this,
                                cameraSelector,
                                preview,
                                imageAnalysis
                        );


                    } catch (
                            ExecutionException
                                    |
                                    InterruptedException e
                    ) {

                        Toast.makeText(
                                this,
                                "Не удалось запустить камеру: "
                                        +
                                        e.getMessage(),
                                Toast.LENGTH_LONG
                        ).show();

                        finish();
                    }

                },
                ContextCompat.getMainExecutor(
                        this
                )
        );
    }


    // =====================================================
    // ANALYZE FRAME
    // =====================================================

    private void analyzeFrame(
            @NonNull ImageProxy imageProxy
    ) {

        if (
                resultSent.get()
        ) {

            imageProxy.close();

            return;
        }


        if (
                imageProxy.getImage()
                        ==
                        null
        ) {

            imageProxy.close();

            return;
        }


        InputImage image =
                InputImage.fromMediaImage(
                        imageProxy.getImage(),
                        imageProxy
                                .getImageInfo()
                                .getRotationDegrees()
                );


        barcodeScanner
                .process(
                        image
                )

                .addOnSuccessListener(
                        barcodes -> {

                            if (
                                    resultSent.get()
                            ) {

                                return;
                            }

                            for (
                                    Barcode barcode
                                    :
                                    barcodes
                            ) {

                                String rawValue =
                                        barcode
                                                .getRawValue();

                                if (
                                        rawValue != null
                                                &&
                                                !rawValue
                                                        .trim()
                                                        .isEmpty()
                                ) {

                                    if (
                                            resultSent.compareAndSet(
                                                    false,
                                                    true
                                            )
                                    ) {

                                        returnBarcode(
                                                rawValue.trim()
                                        );
                                    }

                                    break;
                                }
                            }
                        }
                )

                .addOnFailureListener(
                        exception -> {

                            // Ошибка одного кадра
                            // не закрывает сканер.
                        }
                )

                .addOnCompleteListener(
                        task ->
                                imageProxy.close()
                );
    }


    // =====================================================
    // RETURN BARCODE
    // =====================================================

    private void returnBarcode(
            String barcode
    ) {

        Intent result =
                new Intent();

        result.putExtra(
                "barcode",
                barcode
        );

        result.putExtra(
                "manual",
                false
        );

        setResult(
                RESULT_OK,
                result
        );

        finish();
    }


    // =====================================================
    // MANUAL ENTRY
    // =====================================================

    private void returnManual() {

        if (
                !resultSent.compareAndSet(
                        false,
                        true
                )
        ) {

            return;
        }

        Intent result =
                new Intent();

        result.putExtra(
                "manual",
                true
        );

        setResult(
                RESULT_OK,
                result
        );

        finish();
    }


    // =====================================================
    // DESTROY
    // =====================================================

    @Override
    protected void onDestroy() {

        super.onDestroy();

        if (
                barcodeScanner
                        !=
                        null
        ) {

            barcodeScanner.close();
        }

        if (
                cameraExecutor
                        !=
                        null
        ) {

            cameraExecutor.shutdown();
        }
    }
}
