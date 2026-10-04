/* SPDX-License-Identifier: Apache-2.0 */
package com.xiaomi.camera.mivi;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Log;
import java.lang.reflect.Method;

/** Keeps user-initiated MIVI processing eligible for camera access on AOSP. */
public final class FlouriteProcessingService extends Service implements Runnable {
    private static final String TAG = "FlouritePhotoProcessing";
    private static final String CHANNEL = "flourite_photo_processing";
    private static final int NOTIFICATION = 0x464c5243;
    private static final long MAX_PROCESSING_MS = 120_000;
    private static final long DRAIN_MS = 2_000;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private long deadline;
    private long idleSince;
    private Method hasTasks;

    /** Called immediately after a shutter task is registered, while the app is visible. */
    public static void start(Context context) {
        if (context == null) return;
        try {
            context.startForegroundService(new Intent(context, FlouriteProcessingService.class));
        } catch (RuntimeException e) {
            // Revoked permissions/background-start restrictions remain effective.
            Log.w(TAG, "Cannot start photo processing foreground service", e);
        }
    }

    @Override public IBinder onBind(Intent intent) { return null; }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        try {
            if (hasTasks == null) {
                hasTasks = Class.forName("com.xiaomi.camera.mivi.MIVICaptureManager")
                        .getMethod("hasParallelTaskData");
            }
            NotificationManager manager = getSystemService(NotificationManager.class);
            manager.createNotificationChannel(new NotificationChannel(
                    CHANNEL, "Photo processing", NotificationManager.IMPORTANCE_LOW));
            Notification notification = new Notification.Builder(this, CHANNEL)
                    .setSmallIcon(android.R.drawable.ic_menu_camera)
                    .setContentTitle(getApplicationInfo().loadLabel(getPackageManager()))
                    .setContentText("Processing photos")
                    .setCategory(Notification.CATEGORY_PROGRESS)
                    .setOngoing(true).setOnlyAlertOnce(true).build();
            startForeground(NOTIFICATION, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_CAMERA);
            deadline = SystemClock.elapsedRealtime() + MAX_PROCESSING_MS;
            idleSince = 0;
            handler.removeCallbacks(this);
            handler.post(this);
        } catch (ReflectiveOperationException | RuntimeException e) {
            Log.w(TAG, "Photo processing foreground service unavailable", e);
            finish();
        }
        return START_NOT_STICKY;
    }

    @Override public void run() {
        try {
            long now = SystemClock.elapsedRealtime();
            if (now >= deadline) {
                Log.w(TAG, "Photo processing foreground deadline reached");
                finish();
                return;
            }
            boolean pending = Boolean.TRUE.equals(hasTasks.invoke(null));
            if (pending) {
                idleSince = 0;
            } else if (idleSince == 0) {
                idleSince = now;
            } else if (now - idleSince >= DRAIN_MS) {
                finish();
                return;
            }
            handler.postDelayed(this, 1_000);
        } catch (ReflectiveOperationException | RuntimeException e) {
            Log.w(TAG, "Cannot inspect pending photo tasks", e);
            finish();
        }
    }

    private void finish() {
        handler.removeCallbacks(this);
        stopForeground(STOP_FOREGROUND_REMOVE);
        stopSelf();
    }

    @Override public void onDestroy() {
        handler.removeCallbacks(this);
        stopForeground(STOP_FOREGROUND_REMOVE);
        super.onDestroy();
    }
}
