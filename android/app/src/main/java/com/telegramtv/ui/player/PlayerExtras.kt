package com.telegramtv.ui.player

import android.content.ActivityNotFoundException
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.unit.dp

/** Shared by TV and mobile; buttons support keyboard/D-pad focus. */
@Composable
fun PlayerExtras(viewModel: PlayerViewModel, state: PlayerUiState) {
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let(viewModel::addLocalSubtitle)
    }
    if (state.showAddSubtitle) {
        val firstFocus = remember { FocusRequester() }
        AlertDialog(
            onDismissRequest = viewModel::dismissAddSubtitle,
            title = { Text("Add subtitle") },
            text = {
                Column(Modifier.heightIn(max = 380.dp).verticalScroll(rememberScrollState())) {
                    Text("Latest 4 subtitles from your Telegram bot chat • closest filename first")
                    if (state.loadingSubtitles) CircularProgressIndicator(Modifier.padding(12.dp))
                    state.subtitleError?.let {
                        Text(it)
                        TextButton(onClick = viewModel::showAddSubtitle) { Text("Retry") }
                    }
                    if (!state.loadingSubtitles && state.subtitleError == null && state.externalSubtitles.isEmpty()) {
                        Text("No subtitles found. Send an .srt, .vtt, .ass or .ssa file to the bot, then retry.")
                        TextButton(onClick = viewModel::showAddSubtitle) { Text("Retry") }
                    }
                    state.externalSubtitles.forEach { file ->
                        OutlinedButton(onClick = { viewModel.addTelegramSubtitle(file) },
                            modifier = Modifier.fillMaxWidth()) {
                            Column(Modifier.fillMaxWidth()) {
                                Text(file.fileName)
                                Text(file.formattedSize, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                    OutlinedButton(onClick = {
                        try { picker.launch(arrayOf("*/*")) }
                        catch (e: ActivityNotFoundException) {
                            viewModel.showNotice("No file picker installed. Install a file manager that supports Open document, or use Telegram subtitles.")
                        }
                    }, modifier = Modifier.fillMaxWidth().focusRequester(firstFocus)) {
                        Text("Select from device storage")
                    }
                }
            },
            confirmButton = { TextButton(onClick = viewModel::dismissAddSubtitle) { Text("Close") } }
        )
        LaunchedEffect(Unit) { firstFocus.requestFocus() }
    }
    state.playerNotice?.let { notice ->
        AlertDialog(onDismissRequest = viewModel::dismissNotice,
            title = { Text("Player") }, text = { Text(notice) },
            confirmButton = { TextButton(onClick = viewModel::dismissNotice) { Text("OK") } })
    }
}
