/**
 * Marca títulos com cara de INJEÇÃO DE PROMPT ou golpe. O CORVO não usa modelo de linguagem, mas quem consome a API pode usar:
 * texto externo é DADO, nunca instrução. A marca é um aviso para o consumidor não entregar o texto cru a um modelo; nunca apaga a notícia.
 * Determinística e testada; só olha o título. Falso positivo é barato, falso negativo não é: na dúvida, marca.
 */
const PATTERNS: RegExp[] = [
	/ignore (all |any |your |the |previous |prior |above )+/i,
	/disregard (all|any|the|previous|prior|above)/i,
	/\bsystem prompt\b/i,
	/\byou are now\b/i,
	/\bnew instructions?\b/i,
	/\bact as (a |an |the )?(?!usual)/i,
	/\bjailbreak\b|\bdeveloper mode\b|\bDAN mode\b/i,
	/ignore (suas|as|todas as) instru/i,
	/\bbuy now\b|\bcompre agora\b/i,
	/\b(10|50|100|1000)x\b/i,
	/\bguaranteed (profit|returns?)\b|\blucro garantido\b/i,
	/\b(send|transfer|enviar?)\b.{0,30}\b(seed phrase|private key|chave privada|frase de recupera)/i,
	/\bclaim\b.{0,25}\bairdrop\b|\bairdrop\b.{0,25}\bclaim\b/i,
	/<\s*script|javascript:|data:text\/html/i,
];

export function isSuspicious(title: string): boolean {
	return PATTERNS.some((p) => p.test(title));
}
