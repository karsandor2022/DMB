module.exports = {
    name: 'seek',
    description: 'Jump to a specific time in the song',
    options: [{ name: 'seconds', type: 4, description: 'Seconds to jump forward (or negative for back)', required: true }],
    async execute(client, interaction) {
        const seconds = interaction.options.getInteger('seconds');
        const ms = seconds * 1000;

        if (client.mode === 'LOCAL') {
            const queue = client.player.nodes.get(interaction.guild.id);
            if (!queue || !queue.isPlaying()) return interaction.reply({ content: "❌ Nothing playing.", ephemeral: true });
            
            const newTime = queue.node.streamTime + ms;
            await queue.node.seek(newTime);
            return interaction.reply(`⏩ **Seeked** to ${Math.floor(newTime / 1000)}s`);
        } else {
            const player = client.shoukaku.getNode().players.get(interaction.guild.id);
            if (!player) return interaction.reply({ content: "❌ Nothing playing.", ephemeral: true });
            
            const newTime = player.position + ms;
            player.seekTo(newTime);
            return interaction.reply(`⏩ **Seeked** to ${Math.floor(newTime / 1000)}s`);
        }
    }
};