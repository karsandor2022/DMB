const { EmbedBuilder } = require('discord.js');
module.exports = {
    name: 'setupbot',
    description: '[Config] Create a dedicated music dashboard channel',
    async execute(client, interaction) {
        const embed = new EmbedBuilder()
            .setTitle('🎵 Music Dashboard')
            .setDescription('Join a voice channel and use /play to start music.')
            .setColor('#2f3136');
        await interaction.channel.send({ embeds: [embed] });
        interaction.reply({ content: "✅ Dashboard created.", ephemeral: true });
    }
};