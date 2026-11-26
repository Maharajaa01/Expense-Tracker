import { dialog } from 'frappe-ui'
import { useSyncStore } from '@/stores/sync'
import { csrfToken } from './boot'

/**
 * End the Frappe session, then go to the login page. Anything stored on this
 * device for offline use is wiped first; unsynced changes need confirmation.
 */
export async function logout(): Promise<void> {
  const sync = useSyncStore()
  const unsynced = sync.items.length
  if (unsynced) {
    dialog.danger({
      title: 'Log out and lose unsynced changes?',
      message: `${unsynced} ${unsynced === 1 ? 'change has' : 'changes have'} not reached your account yet. Logging out deletes ${unsynced === 1 ? 'it' : 'them'} from this device. Connect to the internet first to keep ${unsynced === 1 ? 'it' : 'them'}.`,
      confirmLabel: 'Log out anyway',
      onConfirm: () => endSession(),
    })
    return
  }
  await endSession()
}

async function endSession(): Promise<void> {
  await useSyncStore().clearForLogout()
  try {
    await fetch('/api/method/logout', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-Frappe-CSRF-Token': csrfToken() },
    })
  } finally {
    window.location.href = '/login?redirect-to=/expense'
  }
}
