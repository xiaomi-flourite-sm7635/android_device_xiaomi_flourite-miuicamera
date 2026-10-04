#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Execute the real Java helper against host-only Android fakes (never packaged).

This tests scheduling/cleanup, not Android's foreground-service permission rules.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

CAMERA = Path(__file__).resolve().parents[1]
ROM = CAMERA.parents[2]
JDK = ROM / 'prebuilts/jdk/jdk21/linux-x86/bin'

FAKES = {
    'android/R.java': 'package android; public class R { public static class drawable { public static final int ic_menu_camera=1; }}',
    'android/os/IBinder.java': 'package android.os; public interface IBinder {}',
    'android/os/Looper.java': 'package android.os; public class Looper { public static Looper getMainLooper() { return new Looper(); }}',
    'android/os/SystemClock.java': 'package android.os; public class SystemClock { public static long now=1000; public static long elapsedRealtime() { return now; }}',
    'android/os/Handler.java': '''package android.os; public class Handler {
        public static Runnable pending; public Handler(Looper l) {}
        public void removeCallbacks(Runnable r) { if (pending==r) pending=null; }
        public void post(Runnable r) { pending=r; }
        public void postDelayed(Runnable r, long delay) { pending=r; }
    }''',
    'android/util/Log.java': '''package android.util; public class Log {
        public static int w(String t,String m) { return 0; }
        public static int w(String t,String m,Throwable e) { return 0; }
    }''',
    'android/content/Intent.java': 'package android.content; public class Intent { public Intent(Context c,Class<?> s) {} }',
    'android/content/Context.java': '''package android.content; public class Context {
        public boolean denied, requested; public Object startForegroundService(Intent i) {
            requested=true; if(denied) throw new SecurityException(); return null;
        }
        public <T> T getSystemService(Class<T> c) { try { return c.getDeclaredConstructor().newInstance(); }
            catch(Exception e) { throw new RuntimeException(e); } }
        public android.content.pm.ApplicationInfo getApplicationInfo() { return new android.content.pm.ApplicationInfo(); }
        public Object getPackageManager() { return null; }
    }''',
    'android/content/pm/ApplicationInfo.java': 'package android.content.pm; public class ApplicationInfo { public CharSequence loadLabel(Object p) { return "Camera"; }}',
    'android/content/pm/ServiceInfo.java': 'package android.content.pm; public class ServiceInfo { public static final int FOREGROUND_SERVICE_TYPE_CAMERA=0x40; }',
    'android/app/NotificationChannel.java': 'package android.app; public class NotificationChannel { public NotificationChannel(String id,String name,int importance) {} }',
    'android/app/NotificationManager.java': 'package android.app; public class NotificationManager { public static final int IMPORTANCE_LOW=2; public void createNotificationChannel(NotificationChannel c) {} }',
    'android/app/Notification.java': '''package android.app; public class Notification {
        public static final String CATEGORY_PROGRESS="progress";
        public static class Builder {
            public Builder(android.content.Context c,String ch) {}
            public Builder setSmallIcon(int i) { return this; }
            public Builder setContentTitle(CharSequence s) { return this; }
            public Builder setContentText(CharSequence s) { return this; }
            public Builder setCategory(String s) { return this; }
            public Builder setOngoing(boolean b) { return this; }
            public Builder setOnlyAlertOnce(boolean b) { return this; }
            public Notification build() { return new Notification(); }
        }
    }''',
    'android/app/Service.java': '''package android.app; public class Service extends android.content.Context {
        public static final int START_NOT_STICKY=2,STOP_FOREGROUND_REMOVE=1;
        public boolean foreground,stopped; public int type;
        public android.os.IBinder onBind(android.content.Intent i) { return null; }
        public int onStartCommand(android.content.Intent i,int f,int id) { return 0; }
        public void startForeground(int id,Notification n,int t) {
            if(denied) throw new SecurityException(); foreground=true; type=t;
        }
        public void stopForeground(int f) { foreground=false; }
        public void stopSelf() { stopped=true; }
        public void onDestroy() {}
    }''',
    'com/xiaomi/camera/mivi/MIVICaptureManager.java': '''package com.xiaomi.camera.mivi;
        public class MIVICaptureManager { public static boolean tasks=true,broken;
            public static boolean hasParallelTaskData() {
                if(broken) throw new IllegalStateException(); return tasks;
            }
        }
    ''',
    'LifecycleTest.java': '''import android.os.*;
        import com.xiaomi.camera.mivi.*;
        public class LifecycleTest {
            static void check(boolean b,String m) { if(!b) throw new AssertionError(m); }
            static FlouriteProcessingService start() {
                FlouriteProcessingService s=new FlouriteProcessingService();
                check(s.onStartCommand(null,0,1)==2,"not sticky");
                check(s.foreground && s.type==0x40,"camera foreground type");
                s.run(); return s;
            }
            static void tick(FlouriteProcessingService s,long ms) { SystemClock.now+=ms; s.run(); }
            static void stopped(FlouriteProcessingService s) {
                check(s.stopped && !s.foreground && Handler.pending==null,"cleanup");
            }
            public static void main(String[] args) {
                String scenario=args[0];
                if(scenario.equals("start-denied")) {
                    android.content.Context c=new android.content.Context(); c.denied=true;
                    FlouriteProcessingService.start(c); check(c.requested,"attempted explicit start");
                    FlouriteProcessingService.start(null); return;
                }
                if(scenario.equals("foreground-denied")) {
                    FlouriteProcessingService s=new FlouriteProcessingService(); s.denied=true;
                    s.onStartCommand(null,0,1); stopped(s); return;
                }
                FlouriteProcessingService s=start();
                switch(scenario) {
                    case "pending": tick(s,1000); check(s.foreground && !s.stopped,"pending kept"); break;
                    case "drain":
                        MIVICaptureManager.tasks=false; tick(s,1000); tick(s,1000);
                        check(!s.stopped,"allow two second drain"); tick(s,1000); stopped(s); break;
                    case "deadline":
                        tick(s,119999); check(!s.stopped,"before deadline"); tick(s,1); stopped(s); break;
                    case "new-capture":
                        tick(s,119000); s.onStartCommand(null,0,2); tick(s,2000);
                        check(!s.stopped,"new capture refreshes deadline"); tick(s,118000); stopped(s); break;
                    case "task-error": MIVICaptureManager.broken=true; tick(s,1000); stopped(s); break;
                    case "destroy": s.onDestroy(); check(!s.foreground && Handler.pending==null,"destroy cleanup"); break;
                    case "task-resumes":
                        MIVICaptureManager.tasks=false; tick(s,1000); MIVICaptureManager.tasks=true; tick(s,1000);
                        MIVICaptureManager.tasks=false; tick(s,1000); check(!s.stopped,"drain reset");
                        tick(s,2000); stopped(s); break;
                    default: throw new AssertionError(scenario);
                }
            }
        }
    ''',
}


class ProcessingLifecycleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configured = os.environ.get('FLOURITE_TEST_JDK')
        cls.javac = str(Path(configured) / 'javac') if configured else str(JDK / 'javac')
        cls.java = str(Path(configured) / 'java') if configured else str(JDK / 'java')
        if not Path(cls.javac).is_file():
            cls.javac, cls.java = shutil.which('javac'), shutil.which('java')
        if not cls.javac or not cls.java:
            raise unittest.SkipTest('Java compiler required')
        cls.temp = tempfile.TemporaryDirectory(prefix='flourite-service-test-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.stage = Path(cls.temp.name)
        sources = []
        for relative, contents in FAKES.items():
            path = cls.stage / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents)
            sources.append(str(path))
        sources.append(str(CAMERA / 'compat/FlouriteProcessingService.java'))
        result = subprocess.run([cls.javac, '-d', str(cls.stage), *sources], capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    def test_lifecycle_scenarios(self):
        for scenario in ('pending', 'drain', 'deadline', 'new-capture', 'task-error',
                         'destroy', 'task-resumes', 'start-denied', 'foreground-denied'):
            with self.subTest(scenario=scenario):
                result = subprocess.run([self.java, '-cp', str(self.stage), 'LifecycleTest', scenario],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
