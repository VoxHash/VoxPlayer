package dev.voxhash.voxplayer.companion

import android.annotation.SuppressLint
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothSocket
import android.content.Context
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.util.UUID
import java.util.concurrent.TimeUnit
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

/**
 * RFCOMM client for the desktop [voxplayer.bt_control] profile.
 * GrapheneOS-friendly — classic Bluetooth only, no Google Nearby.
 */
class BluetoothControl(private val context: Context) {
    companion object {
        val SERVICE_UUID: UUID = UUID.fromString("00001101-0000-1000-8000-00805f9b34fb")
        const val FALLBACK_CHANNEL = 5
    }

    data class BondedHint(
        val name: String,
        val address: String,
    )

    private val lock = ReentrantLock()
    private var socket: BluetoothSocket? = null
    private var reader: BufferedReader? = null
    private var writer: OutputStreamWriter? = null

    val connected: Boolean
        get() = lock.withLock { socket?.isConnected == true }

    @SuppressLint("MissingPermission")
    fun bondedDevices(): List<BondedHint> {
        val mgr = context.getSystemService(BluetoothManager::class.java) ?: return emptyList()
        val adapter = mgr.adapter ?: return emptyList()
        if (!adapter.isEnabled) return emptyList()
        return try {
            adapter.bondedDevices?.map {
                BondedHint(name = it.name ?: it.address, address = it.address)
            }?.sortedBy { it.name.lowercase() } ?: emptyList()
        } catch (_: SecurityException) {
            emptyList()
        }
    }

    @SuppressLint("MissingPermission")
    fun connect(address: String, timeoutMs: Long = 12_000): JSONObject {
        disconnect()
        val mgr = context.getSystemService(BluetoothManager::class.java)
            ?: throw IllegalStateException("Bluetooth unavailable")
        val adapter = mgr.adapter ?: throw IllegalStateException("No Bluetooth adapter")
        if (!adapter.isEnabled) throw IllegalStateException("Bluetooth is off — enable it to Connect")
        val device = adapter.getRemoteDevice(address)
        adapter.cancelDiscovery()
        val sock = openSocket(device)
        sock.connect()
        // Wait briefly for hello line
        val r = BufferedReader(InputStreamReader(sock.inputStream, Charsets.UTF_8))
        val w = OutputStreamWriter(sock.outputStream, Charsets.UTF_8)
        lock.withLock {
            socket = sock
            reader = r
            writer = w
        }
        return readLine(timeoutMs) ?: JSONObject().put("ok", true)
    }

    @SuppressLint("MissingPermission")
    private fun openSocket(device: BluetoothDevice): BluetoothSocket {
        return try {
            device.createRfcommSocketToServiceRecord(SERVICE_UUID)
        } catch (_: Exception) {
            // Fallback: insecure channel bind used by desktop AF_BLUETOOTH server
            try {
                val m = device.javaClass.getMethod("createRfcommSocket", Int::class.javaPrimitiveType)
                @Suppress("UNCHECKED_CAST")
                m.invoke(device, FALLBACK_CHANNEL) as BluetoothSocket
            } catch (e: Exception) {
                device.createInsecureRfcommSocketToServiceRecord(SERVICE_UUID)
            }
        }
    }

    fun disconnect() {
        lock.withLock {
            try {
                writer?.close()
            } catch (_: Exception) {
            }
            try {
                reader?.close()
            } catch (_: Exception) {
            }
            try {
                socket?.close()
            } catch (_: Exception) {
            }
            writer = null
            reader = null
            socket = null
        }
    }

    fun command(cmd: String, extra: JSONObject = JSONObject()): JSONObject {
        val payload = JSONObject(extra.toString()).put("cmd", cmd)
        lock.withLock {
            val w = writer ?: throw IllegalStateException("Not connected over Bluetooth")
            val r = reader ?: throw IllegalStateException("Not connected over Bluetooth")
            w.write(payload.toString())
            w.write("\n")
            w.flush()
            val line = r.readLine() ?: throw IllegalStateException("Bluetooth connection closed")
            return JSONObject(line)
        }
    }

    fun status(): JSONObject = command("status")
    fun playPause(): JSONObject = command("playpause")
    fun stop(): JSONObject = command("stop")
    fun next(): JSONObject = command("next")
    fun previous(): JSONObject = command("previous")
    fun volume(percent: Int): JSONObject =
        command("volume", JSONObject().put("percent", percent.coerceIn(0, 200)))
    fun seekRelative(ms: Long): JSONObject =
        command("seek", JSONObject().put("relative_ms", ms))
    fun library(limit: Int = 100): JSONObject =
        command("library", JSONObject().put("limit", limit).put("offset", 0))
    fun playlists(): JSONObject = command("playlists")
    fun podcasts(): JSONObject = command("podcasts")

    private fun readLine(timeoutMs: Long): JSONObject? {
        val r = lock.withLock { reader } ?: return null
        val deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(timeoutMs)
        while (System.nanoTime() < deadline) {
            if (r.ready()) {
                val line = r.readLine() ?: return null
                return JSONObject(line)
            }
            Thread.sleep(40)
        }
        return null
    }
}
