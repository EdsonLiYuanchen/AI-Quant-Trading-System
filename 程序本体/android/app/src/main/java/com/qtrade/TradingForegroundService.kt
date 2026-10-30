package com.qtrade

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat

/**
 * 前台服务：启动 Python 的 headless_server.start_server() 并保持通知显示。
 * 在 `TradingForegroundService::` 中启动 Python（Chaquopy）— Python 侧调用
 * `start_server(host, port, token)` 启动 HTTP 服务器，在后台线程 running。
 * 前台通知保持用户可见；服务可自行停止。
 */
class TradingForegroundService : Service() {
    private var _notifId = 0
    private var _running = false

    companion object {
        const val CHANNEL_ID = "trading_service_channel"
        const val NOTIF_ID = 1
        const val ARG_HOST = "host"
        const val ARG_PORT = "port"
        const val ARG_TOKEN = "token"

        // 通知标题
        const val NOTIF_TITLE = "AI 量化交易系统"
    }

    override fun onCreate() {
        super.onCreate()
        if (_running) return
        _running = true
        startForeground(NOTIF_ID, buildNotification("交易引擎运行中"))
        // 启动 Python 服务器（非阻塞，守护线程）
        startPythonServer()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

    override fun onDestroy() {
        _running = false
        // 通知销毁
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.cancel(NOTIF_ID)
        super.onDestroy()
    }

    private fun startPythonServer() {
        // 启动 Python interpreter + headless_server 的 start_server
        if (!Python.isSupported) return
        val py = Python.getInstance()
        try {
            // 调用 Python 函数的 start_server(host, port, token) — 返回值是 dict
            // 启动线程并让它守护线程持续运行（服务进程不死亡）
            py.getModule("headless_server").callAttr("start_server",
                "0.0.0.0",
                8000,
                intent?.getStringExtra(ARG_TOKEN)
            )
        } catch (e: Exception) {
            Log.e("TradingService", "Python 启动失败: ${e.message}")
        }
    }

    private fun buildNotification(title: String): Notification {
        val pIntent = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(NOTIF_TITLE)
            .setContentText(title)
            .setSmallIcon(android.R.drawable.ic_lock_idle_lock)
            .setContentIntent(pIntent)
            .setOngoing(true)
            .build()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
