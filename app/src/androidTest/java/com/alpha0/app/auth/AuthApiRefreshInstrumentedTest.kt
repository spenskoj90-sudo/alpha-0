package com.alpha0.app.auth

import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.net.ServerSocket
import kotlin.concurrent.thread

@RunWith(AndroidJUnit4::class)
class AuthApiRefreshInstrumentedTest {
    @Test
    fun refreshPostsRefreshTokenAndParsesReplacementSession() {
        ServerSocket(0).use { server ->
            val response = """
                {"session_token":"new-access","refresh_token":"new-refresh","scopes":["account:read"]}
            """.trimIndent()
            val requestSeen = arrayOfNulls<String>(1)
            val worker = thread {
                server.accept().use { socket ->
                    val request = socket.getInputStream().bufferedReader().readText()
                    requestSeen[0] = request
                    val bytes = response.toByteArray(Charsets.UTF_8)
                    socket.getOutputStream().bufferedWriter().use { writer ->
                        writer.write("HTTP/1.1 200 OK\r\n")
                        writer.write("Content-Type: application/json\r\n")
                        writer.write("Content-Length: ${bytes.size}\r\n")
                        writer.write("Connection: close\r\n\r\n")
                        writer.flush()
                        socket.getOutputStream().write(bytes)
                        socket.getOutputStream().flush()
                    }
                }
            }

            val result = AuthApi("http://127.0.0.1:${server.localPort}").refresh("refresh-token")
            worker.join(2_000)

            assertTrue(result is AuthApi.Result.Success)
            val session = (result as AuthApi.Result.Success).session
            assertEquals("new-access", session.accessToken)
            assertEquals("new-refresh", session.refreshToken)
            assertEquals(listOf("account:read"), session.scopes)
            assertTrue(requestSeen[0]?.contains("POST /v1/sessions/refresh HTTP/1.1") == true)
            assertTrue(requestSeen[0]?.contains("refresh_token") == true)
        }
    }
}
