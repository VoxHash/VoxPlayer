package dev.voxhash.voxplayer.companion

import android.content.Context
import android.net.wifi.WifiManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.InetSocketAddress
import java.nio.charset.StandardCharsets

data class DiscoveredDesktop(
    val name: String,
    val host: String,
    val port: Int,
    val version: String,
    val via: String = "wifi",
)

/**
 * UDP discovery for desktop [DiscoveryBeacon] (port 17891).
 * GrapheneOS-friendly: no Google Nearby / Play Services.
 */
object LanDiscovery {
    const val DISCOVERY_PORT = 17891
    private val PROBE = "VOXPLAYER_DISCOVER?".toByteArray(StandardCharsets.UTF_8)

    suspend fun scan(context: Context, timeoutMs: Int = 2500): List<DiscoveredDesktop> =
        withContext(Dispatchers.IO) {
            val found = LinkedHashMap<String, DiscoveredDesktop>()
            val wifi = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
            val lock = wifi?.createMulticastLock("voxplayer-discover")?.apply {
                setReferenceCounted(true)
                acquire()
            }
            try {
                DatagramSocket().use { sock ->
                    sock.broadcast = true
                    sock.soTimeout = 400
                    sock.bind(InetSocketAddress(0))
                    val buf = ByteArray(2048)
                    // Probe directed broadcasts + limited broadcast
                    val targets = probeTargets(context)
                    for (addr in targets) {
                        try {
                            sock.send(DatagramPacket(PROBE, PROBE.size, addr, DISCOVERY_PORT))
                        } catch (_: Exception) {
                        }
                    }
                    val deadline = System.currentTimeMillis() + timeoutMs
                    while (System.currentTimeMillis() < deadline) {
                        try {
                            val packet = DatagramPacket(buf, buf.size)
                            sock.receive(packet)
                            parseAnnounce(packet)?.let { d ->
                                found["${d.host}:${d.port}"] = d
                            }
                        } catch (_: Exception) {
                            // timeout — keep looping until deadline
                        }
                    }
                }
            } finally {
                try {
                    lock?.release()
                } catch (_: Exception) {
                }
            }
            found.values.toList()
        }

    private fun parseAnnounce(packet: DatagramPacket): DiscoveredDesktop? {
        val text = String(packet.data, 0, packet.length, StandardCharsets.UTF_8).trim()
        if (!text.startsWith("{")) return null
        return try {
            val o = JSONObject(text)
            if (o.optString("service") != "voxplayer") return null
            val host = o.optString("host").ifBlank { packet.address.hostAddress ?: return null }
            val port = o.optInt("port", 17890)
            DiscoveredDesktop(
                name = o.optString("name", "VoxPlayer"),
                host = host,
                port = port,
                version = o.optString("version", ""),
                via = "wifi",
            )
        } catch (_: Exception) {
            null
        }
    }

    private fun probeTargets(context: Context): List<InetAddress> {
        val out = mutableListOf<InetAddress>()
        try {
            out.add(InetAddress.getByName("255.255.255.255"))
        } catch (_: Exception) {
        }
        try {
            val wm = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            @Suppress("DEPRECATION")
            val ip = wm.connectionInfo?.ipAddress ?: 0
            if (ip != 0) {
                val b0 = ip and 0xff
                val b1 = ip shr 8 and 0xff
                val b2 = ip shr 16 and 0xff
                out.add(InetAddress.getByName("$b0.$b1.$b2.255"))
            }
        } catch (_: Exception) {
        }
        return out
    }
}
