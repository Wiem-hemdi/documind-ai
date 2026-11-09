export async function readApiResponse(response) {
  const responseText = await response.text()
  let result = null

  if (responseText.trim()) {
    try {
      result = JSON.parse(responseText)
    } catch {
      if (!response.ok) {
        throw new Error(
          `Le serveur a répondu avec une erreur (${response.status}). Vérifiez que l’API backend est démarrée.`,
        )
      }
      throw new Error('La réponse du serveur est invalide.')
    }
  }

  if (!response.ok) {
    throw new Error(
      result?.message ||
        `La requête a échoué (${response.status}). Vérifiez que l’API backend est démarrée.`,
    )
  }

  if (!result) {
    throw new Error('Le serveur a renvoyé une réponse vide. Vérifiez que l’API backend est démarrée.')
  }

  return result
}
