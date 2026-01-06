module.exports = {
    name: 'pause',
    description: 'Pause the currently playing song',
    async execute(client, interaction) {
        if (client.mode === 'LOCAL') {
            const queue = client.player.nodes.get(interaction.guild.id);
            if (!queue || !queue.isPlaying()) return interaction.reply({ content: "❌ Nothing is playing.", ephemeral: true });
            
            queue.node.pause();
            return interaction.reply("II **Paused**");
        } else {
            const player = client.shoukaku.getNode().players.get(interaction.guild.id);
            if (!player) return interaction.reply({ content: "❌ Nothing is playing.", ephemeral: true });
            
            player.setPaused(true);
            return interaction.reply("II **Paused**");
        }
    }
};