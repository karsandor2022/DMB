module.exports = {
    name: 'queue',
    description: 'Display the list of upcoming songs',
    async execute(client, interaction) {
        if (client.mode === 'LOCAL') {
            const queue = client.player.nodes.get(interaction.guild.id);
            if (!queue || !queue.tracks.size) return interaction.reply({ content: "❌ Queue is empty.", ephemeral: true });

            const tracks = queue.tracks.map((t, i) => `${i+1}. **${t.title}**`).slice(0, 10).join('\n');
            const remaining = queue.tracks.size - 10;
            
            return interaction.reply(`📜 **Current Queue**\n${tracks}\n${remaining > 0 ? `...and ${remaining} more` : ''}`);
        } else {
            return interaction.reply({ content: "❌ Queue display is limited in Remote mode (Lavalink doesn't store queue natively).", ephemeral: true });
        }
    }
};