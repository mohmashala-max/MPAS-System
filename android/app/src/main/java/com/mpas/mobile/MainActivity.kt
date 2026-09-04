package com.mpas.mobile

import android.os.Bundle
import android.content.Intent
import android.view.Gravity
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import androidx.lifecycle.lifecycleScope
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import com.mpas.mobile.auth.AuthRepository
import com.mpas.mobile.data.InspectionRepository
import com.mpas.mobile.sync.enqueueInspectionSync
import androidx.work.WorkManager
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private lateinit var imageUriField: EditText
    private val imagePicker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let {
            contentResolver.takePersistableUriPermission(
                it,
                Intent.FLAG_GRANT_READ_URI_PERMISSION
            )
            imageUriField.setText(it.toString())
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val status = TextView(this).apply { text = "M-PAS Field" }
        val username = EditText(this).apply { hint = "Username" }
        val password = EditText(this).apply { hint = "Password"; inputType = 0x81 }
        val login = Button(this).apply { text = "Sign in" }
        val facility = EditText(this).apply { hint = "Facility ID"; isEnabled = false }
        val trap = EditText(this).apply { hint = "Trap ID"; isEnabled = false }
        imageUriField = EditText(this).apply { hint = "Image URI"; isEnabled = false }
        val pickImage = Button(this).apply { text = "Choose image"; isEnabled = false }
        val queue = Button(this).apply { text = "Queue offline inspection"; isEnabled = false }
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(48, 48, 48, 48)
            addView(status)
            addView(username)
            addView(password)
            addView(login)
            addView(facility)
            addView(trap)
            addView(imageUriField)
            addView(pickImage)
            addView(queue)
        }
        setContentView(layout)

        val auth = AuthRepository(this, BuildConfig.MPAS_API_BASE_URL)
        val inspections = InspectionRepository((application as MpasApplication).database.inspectionDao())
        login.setOnClickListener {
            login.isEnabled = false
            status.text = "Signing in..."
            lifecycleScope.launch {
                auth.login(username.text.toString(), password.text.toString())
                    .onSuccess {
                        status.text = "Ready for offline inspections"
                        facility.isEnabled = true
                        trap.isEnabled = true
                        imageUriField.isEnabled = true
                        pickImage.isEnabled = true
                        queue.isEnabled = true
                    }
                    .onFailure { status.text = "Sign-in failed: ${it.message.orEmpty()}" }
                login.isEnabled = true
            }
        }
        pickImage.setOnClickListener {
            imagePicker.launch(arrayOf("image/*"))
        }
        queue.setOnClickListener {
            val facilityId = facility.text.toString().trim()
            val trapId = trap.text.toString().trim()
            val imageUri = imageUriField.text.toString().trim()
            if (facilityId.isEmpty() || trapId.isEmpty() || imageUri.isEmpty()) {
                status.text = "Facility, trap, and image are required"
                return@setOnClickListener
            }
            lifecycleScope.launch {
                inspections.queue(
                    facilityId,
                    trapId,
                    imageUri
                )
                enqueueInspectionSync(WorkManager.getInstance(this@MainActivity))
                status.text = "Inspection queued offline"
            }
        }
    }

}
