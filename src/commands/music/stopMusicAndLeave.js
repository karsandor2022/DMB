module.exports = {
    name: 'stop',
    description: 'Stop the music and disconnect the bot',
    async execute(client, interaction) {
        if (client.mode === 'LOCAL') {
            const queue = client.player.nodes.get(interaction.guild.id);
            if (queue) queue.delete();
        } else {
            const player = client.shoukaku.getNode().players.get(interaction.guild.id);
            if (player) {
                player.stopTrack();
                client.shoukaku.leaveVoiceChannel(interaction.guild.id);
            }
        }
        return interaction.reply("⏹️ **Stopped and Disconnected**");
    }
};