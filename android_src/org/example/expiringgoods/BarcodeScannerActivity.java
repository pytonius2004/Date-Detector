package org.example.expiringgoods;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.ViewGroup;
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
import com.google.mlkit.vision.barcode.BarcodeScanning;
import com.google.mlkit.vision.barcode.BarcodeScannerOptions;
import com.google.mlkit.vision.barcode.common.Barcode;
import com.google.mlkit.vision.common.InputImage;

import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import java.util.concurrent.atomic.AtomicBoolean;


public class BarcodeScannerActivity
        extends ComponentActivity {

    private static final int CAMERA_PERMISSION_REQUEST = 6001;

    private PreviewView previewView;

    private TextView instructionText;

    private Button manualButton;

    private ExecutorService cameraExecutor;

    private BarcodeScanner barcodeScanner;

    private ProcessCameraProvider cameraProvider;

    private ImageAnalysis imageAnalysis;

    private final AtomicBoolean resultSent =
            new AtomicBoolean(false);


    @Override
    protected void onCreate(
            Bundle savedInstanceState
    ) {

        super.onCreate(
                savedInstanceState
        );


        // =================================================
        // Root layout
        // =================================================

        FrameLayout root =
                new FrameLayout(this);

        root.setBackgroundColor(
                Color.BLACK
        );


        // =================================================
        // Camera preview
        // =================================================

        previewView =
                new PreviewView(this);

        previewView.setImplementationMode(
                PreviewView.ImplementationMode.COMPATIBLE
        );


        FrameLayout.LayoutParams cameraParams =
                new FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT
                );

        root.addView(
                previewView,
                cameraParams
        );


        // =================================================
        // Instruction text
        // =================================================

        instructionText =
                new TextView(this);

        instructionText.setText(
                "Наведите камеру на штрихкод"
        );

        instructionText.setTextColor(
                Color.WHITE
        );

        instructionText.setTextSize(
                18
        );

        instructionText.setGravity(
                Gravity.CENTER
        );

        instructionText.setPadding(
                24,
                20,
                24,
                20
        );

        instructionText.setBackgroundColor(
                0x88000000
        );


        FrameLayout.LayoutParams textParams =
                new FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                );

        textParams.gravity =
                Gravity.TOP;

        textParams.topMargin = 40;


        root.addView(
                instructionText,
                textParams
        );


        // =================================================
        // Manual input button
        // =================================================

        manualButton =
                new Button(this);

        manualButton.setText(
                "Добавить вручную"
        );

        manualButton.setTextSize(
                16
        );

        manualButton.setTextColor(
                Color.WHITE
        );

        manualButton.setBackgroundColor(
                0xDD222222
        );

        manualButton.setAllCaps(
                false
        );


        FrameLayout.LayoutParams manualParams =
                new FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        70
                );

        manualParams.gravity =
                Gravity.BOTTOM;

        manualParams.leftMargin = 30;
        manualParams.rightMargin = 30;
        manualParams.bottomMargin = 35;


        root.addView(
                manualButton,
                manualParams
        );


        manualButton.setOnClickListener(
                view -> returnManualInput()
        );


        setContentView(
                root
        );


        // =================================================
        // Executors / ML Kit
        // =================================================

        cameraExecutor =
                Executors.newSingleThreadExecutor();


        BarcodeScannerOptions options =
                new BarcodeScannerOptions.Builder()
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


        checkCameraPermission();
    }


    // =====================================================
    // Camera permission
    // =====================================================

    private void checkCameraPermission() {

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
                        "Для сканирования нужен доступ к камере.",
                        Toast.LENGTH_LONG
                ).show();

                setResult(
                        RESULT_CANCELED
                );

                finish();
            }
        }
    }


    // =====================================================
    // Start camera
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

                        cameraProvider =
                                cameraProviderFuture.get();


                        Preview preview =
                                new Preview.Builder()
                                        .build();


                        preview.setSurfaceProvider(
                                previewView
                                        .getSurfaceProvider()
                        );


                        imageAnalysis =
                                new ImageAnalysis.Builder()
                                        .setBackpressureStrategy(
                                                ImageAnalysis
                                                        .STRATEGY_KEEP_ONLY_LATEST
                                        )
                                        .build();


                        imageAnalysis.setAnalyzer(
                                cameraExecutor,
                                this::analyzeFrame
                        );


                        CameraSelector selector =
                                CameraSelector
                                        .DEFAULT_BACK_CAMERA;


                        cameraProvider.unbindAll();


                        cameraProvider.bindToLifecycle(
                                this,
                                selector,
                                preview,
                                imageAnalysis
                        );


                    }
                    catch (
                            ExecutionException
                                    |
                            InterruptedException error
                    ) {

                        Toast.makeText(
                                this,
                                "Не удалось запустить камеру:\n"
                                        +
                                        error.getMessage(),
                                Toast.LENGTH_LONG
                        ).show();


                        setResult(
                                RESULT_CANCELED
                        );

                        finish();
                    }

                },
                ContextCompat.getMainExecutor(
                        this
                )
        );
    }


    // =====================================================
    // Analyze frame
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
                .process(image)

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
                                        barcode.getRawValue();


                                if (
                                        rawValue != null
                                        &&
                                        !rawValue
                                                .trim()
                                                .isEmpty()
                                ) {

                                    if (
                                            resultSent
                                                    .compareAndSet(
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
                        error -> {
                            // Continue scanning.
                        }
                )

                .addOnCompleteListener(
                        task ->
                                imageProxy.close()
                );
    }


    // =====================================================
    // Return barcode to Python
    // =====================================================

    private void returnBarcode(
            String barcode
    ) {

        runOnUiThread(
                () -> {

                    stopCamera();

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
        );
    }


    // =====================================================
    // Manual input
    // =====================================================

    private void returnManualInput() {

        if (
                !resultSent.compareAndSet(
                        false,
                        true
                )
        ) {

            return;
        }


        runOnUiThread(
                () -> {

                    stopCamera();

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
        );
    }


    // =====================================================
    // Stop camera
    // =====================================================

    private void stopCamera() {

        try {

            if (
                    cameraProvider != null
            ) {

                cameraProvider.unbindAll();
            }

        } catch (Exception ignored) {
        }


        try {

            if (
                    imageAnalysis != null
            ) {

                imageAnalysis.clearAnalyzer();
            }

        } catch (Exception ignored) {
        }
    }


    // =====================================================
    // Destroy
    // =====================================================

    @Override
    protected void onDestroy() {

        stopCamera();


        if (
                barcodeScanner != null
        ) {

            barcodeScanner.close();
        }


        if (
                cameraExecutor != null
        ) {

            cameraExecutor.shutdown();
        }


        super.onDestroy();
    }
}
