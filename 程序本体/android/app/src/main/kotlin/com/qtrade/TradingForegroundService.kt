package com.qtrade

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.NotificationCompat
import com.chaquo.python.Python
import com.chaquo.python.hosts.AndroidHost
import com.chaquo.python.webview.WebViewBridge
import com.chaquo.python.webview.PyWebViewBridge
import android.webkit.WebView
import android.webkit.WebViewClient
import org.json.JSONObject

class TradingForegroundService : android.app.Service {
    private var _started = false
    private var _t: android.os.Handler? = null
    private var _tId = 0L

    companion object {
        const val CHANNEL_ID = "trading_foreground"
        const val NOTIFICATION_ID = 1001
        const val PYTHON_PROCESS = "headless_server"
        const val PYTHON_SCRIPT = "start_server"
        const val ARG_HOST = "host"
        const val ARG_PORT = "port"
        const val ARG_TOKEN = "token"

        // 通知内容（用于用户提醒）
        private val notificationText = "AI量化交易系统（模拟盘）正在运行中"
    }

    override fun onCreate() {
        super.onCreate()
        _t = Handler(Looper.getMainLooper())
        // 如果已有实例则跳过
        if (_started) return
        _started = true
        startForeground(NOTIFICATION_ID, buildNotification())
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // 服务启动后立即进入前台
        if (_started && intent?.action == null) {
            return START_STICKY
        }
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        _started = false
        _t?.removeCallbacksAndMessages(null)
        // 通知停止
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.cancel(NOTIFICATION_ID)
        super.onDestroy()
    }

    private fun buildNotification(): Notification {
        val intent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("AI 量化交易系统")
            .setContentText("交易引擎正在运行中（模拟盘）")
            .setSmallIcon(android.R.drawable.ic_lock_idle_lock)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    private fun startPythonService() {
        // 获取 Python 运行器实例
        if (!Python.isSupported) return
        val py = Python.getInstance()
        try {
            val mod = py.getModule(PYTHON_PROCESS)
            // 启动 Python 服务器（非阻塞，主线程被守护）
            mod.callAttr(PYTHON_SCRIPT, "0.0.0.0", 8000, null)
        } catch (e: Exception) {
            // 服务器启动失败 — 服务仍可运行（仅引擎无法恢复）
        }
    }

    // 启动服务
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        _t?.post {
            startForeground(NOTIFICATION_ID, buildNotification())
            startPythonService()
        }
        return START_STICKY
    }
}
